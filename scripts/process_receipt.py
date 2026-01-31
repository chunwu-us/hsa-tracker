#!/usr/bin/env python3
"""
Process receipt images/PDFs using Claude Vision API.
Extracts date, provider, amount, and category from receipts.
Archives to year-based folders for 15-year IRS retention.
"""

import anthropic
import base64
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import csv
import subprocess

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    
    media_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    
    media_type = media_types.get(suffix, 'image/png')
    
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    
    return data, media_type


def pdf_to_image(pdf_path: str) -> str:
    """Convert PDF to temporary PNG image using macOS qlmanage."""
    pdf_path = Path(pdf_path)
    output_dir = Path('/tmp')
    
    # Use Quick Look to generate thumbnail
    subprocess.run([
        'qlmanage', '-t', '-s', '2000', '-o', str(output_dir), str(pdf_path)
    ], capture_output=True)
    
    # Find generated PNG
    png_path = output_dir / f"{pdf_path.name}.png"
    if png_path.exists():
        return str(png_path)
    
    raise RuntimeError(f"Failed to convert PDF: {pdf_path}")


def generate_receipt_id(date: str, provider: str, amount: float) -> str:
    """Generate deterministic receipt ID."""
    seed = f"{date}:{provider}:{amount}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest()[:10].upper()
    return f"HSA{hash_val}"


def is_duplicate(date: str, provider: str, amount: float, csv_path: Path) -> bool:
    """Check if receipt already exists in CSV."""
    if not csv_path.exists():
        return False
    
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row['Date'] == date and 
                abs(float(row['Amount']) - amount) < 0.01):
                return True
    return False


def extract_receipt_info(image_path: str, api_key: str = None) -> dict:
    """Extract receipt information using Claude Vision."""
    
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    image_data, media_type = encode_image(image_path)
    
    prompt = """Analyze this medical receipt/EOB and extract:

1. **Date**: The date of service (format: YYYY-MM-DD)
2. **Provider**: The healthcare provider name
3. **Amount**: The amount paid by patient (not billed, not insurance paid - the patient responsibility/payment)
4. **Category**: One of: Medical, Dental, Vision, Prescription, Mental Health, Other

Return ONLY valid JSON in this exact format:
{
  "date": "YYYY-MM-DD",
  "provider": "Provider Name",
  "amount": 123.45,
  "category": "Medical",
  "notes": "Brief description of service if visible"
}

If you cannot determine a field with confidence, use null for that field."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )
    
    # Parse response
    response_text = message.content[0].text
    
    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    return json.loads(response_text.strip())


def process_receipt(
    receipt_path: str,
    archive_dir: str = None,
    csv_path: str = None,
    api_key: str = None,
    dry_run: bool = False
) -> dict:
    """
    Process a receipt:
    1. Convert PDF to image if needed (temp)
    2. Extract info via Claude Vision
    3. Check for duplicates
    4. Generate receipt ID
    5. Copy ORIGINAL to year-based archive folder
    6. Append to CSV
    7. Clean up temp files
    
    Returns extracted info dict.
    """
    
    receipt_path = Path(receipt_path)
    if not receipt_path.exists():
        raise FileNotFoundError(f"Receipt not found: {receipt_path}")
    
    is_pdf = receipt_path.suffix.lower() == '.pdf'
    temp_image = None
    
    # Convert PDF to image for extraction
    if is_pdf:
        print(f"📄 Converting PDF: {receipt_path.name}")
        temp_image = pdf_to_image(str(receipt_path))
        extract_path = temp_image
    else:
        extract_path = str(receipt_path)
    
    # Extract info
    print(f"🔍 Extracting info from: {receipt_path.name}")
    info = extract_receipt_info(extract_path, api_key)
    print(f"   Date: {info.get('date')}")
    print(f"   Provider: {info.get('provider')}")
    print(f"   Amount: ${info.get('amount')}")
    print(f"   Category: {info.get('category')}")
    
    if info.get('date') is None or info.get('amount') is None:
        print("   ⚠️  Could not extract required fields")
        return info
    
    # Determine year and paths
    year = info['date'][:4]
    
    if archive_dir is None:
        archive_dir = Path(__file__).parent.parent / "receipts" / year
    else:
        archive_dir = Path(archive_dir) / year
    
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "data" / f"hsa_expenses_{year}.csv"
    else:
        csv_path = Path(csv_path)
    
    # Check for duplicates
    if is_duplicate(info['date'], info.get('provider', ''), info['amount'], csv_path):
        print(f"   ⚠️  Duplicate detected - skipping")
        info['duplicate'] = True
        if temp_image:
            Path(temp_image).unlink(missing_ok=True)
        return info
    
    # Generate receipt ID
    receipt_id = generate_receipt_id(
        info['date'],
        info.get('provider', 'Unknown'),
        info['amount']
    )
    info['receipt_id'] = receipt_id
    print(f"   Receipt ID: {receipt_id}")
    
    # Standardized filename (keep original extension)
    provider_slug = (info.get('provider') or 'unknown').lower()
    provider_slug = ''.join(c if c.isalnum() else '_' for c in provider_slug)[:30]
    new_filename = f"{info['date']}_{provider_slug}_{info['amount']}{receipt_path.suffix}"
    archive_path = archive_dir / new_filename
    info['receipt_path'] = f"receipts/{year}/{new_filename}"
    
    if dry_run:
        print(f"   [DRY RUN] Would archive to: {archive_path}")
        print(f"   [DRY RUN] Would append to: {csv_path}")
        if temp_image:
            Path(temp_image).unlink(missing_ok=True)
        return info
    
    # Archive original file
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(receipt_path, archive_path)
    print(f"   ✅ Archived: {new_filename}")
    
    # Append to CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Date', 'Provider', 'Amount', 'Category', 'Receipt_ID', 'Receipt_URL', 'Notes', 'Source'])
        writer.writerow([
            info['date'],
            info.get('provider', ''),
            info['amount'],
            info.get('category', 'Other'),
            receipt_id,
            info['receipt_path'],
            info.get('notes', ''),
            'scan'
        ])
    print(f"   ✅ Added to CSV")
    
    # Clean up temp files
    if temp_image:
        Path(temp_image).unlink(missing_ok=True)
    
    return info


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Process HSA receipt images/PDFs')
    parser.add_argument('receipt', help='Path to receipt (image or PDF)')
    parser.add_argument('--archive-dir', '-a', help='Archive directory for receipts')
    parser.add_argument('--csv', '-c', help='Path to CSV file')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run, no file changes')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON only')
    
    args = parser.parse_args()
    
    try:
        result = process_receipt(
            args.receipt,
            archive_dir=args.archive_dir,
            csv_path=args.csv,
            dry_run=args.dry_run
        )
        
        if args.json:
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
