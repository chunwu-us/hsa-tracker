#!/usr/bin/env python3
"""
Process receipt images using Claude Vision API.
Extracts date, provider, amount, and category from receipt images.
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

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import load_categories


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
        '.pdf': 'application/pdf'
    }
    
    media_type = media_types.get(suffix, 'image/png')
    
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    
    return data, media_type


def generate_receipt_id(date: str, provider: str, amount: float) -> str:
    """Generate deterministic receipt ID."""
    seed = f"{date}:{provider}:{amount}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest()[:10].upper()
    return f"MED{hash_val}"


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
    image_path: str,
    output_dir: str = None,
    csv_path: str = None,
    api_key: str = None,
    dry_run: bool = False
) -> dict:
    """
    Process a receipt image:
    1. Extract info via Claude Vision
    2. Generate receipt ID
    3. Copy to receipts folder with standardized name
    4. Append to CSV
    
    Returns extracted info dict.
    """
    
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Set defaults
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "receipts"
    else:
        output_dir = Path(output_dir)
    
    if csv_path is None:
        year = datetime.now().year
        csv_path = Path(__file__).parent.parent / "data" / f"hsa_expenses_{year}.csv"
    else:
        csv_path = Path(csv_path)
    
    # Extract info
    print(f"📄 Processing: {image_path.name}")
    info = extract_receipt_info(str(image_path), api_key)
    print(f"   Date: {info.get('date')}")
    print(f"   Provider: {info.get('provider')}")
    print(f"   Amount: ${info.get('amount')}")
    print(f"   Category: {info.get('category')}")
    
    if info.get('date') is None or info.get('amount') is None:
        print("   ⚠️  Could not extract required fields")
        return info
    
    # Generate receipt ID
    receipt_id = generate_receipt_id(
        info['date'],
        info.get('provider', 'Unknown'),
        info['amount']
    )
    info['receipt_id'] = receipt_id
    print(f"   Receipt ID: {receipt_id}")
    
    # Standardized filename
    provider_slug = (info.get('provider') or 'unknown').lower()
    provider_slug = ''.join(c if c.isalnum() else '_' for c in provider_slug)[:30]
    new_filename = f"{info['date']}_{provider_slug}_{info['amount']}{image_path.suffix}"
    new_path = output_dir / new_filename
    info['receipt_path'] = f"receipts/{new_filename}"
    
    if dry_run:
        print(f"   [DRY RUN] Would copy to: {new_path}")
        print(f"   [DRY RUN] Would append to: {csv_path}")
        return info
    
    # Copy file
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image_path, new_path)
    print(f"   ✅ Saved: {new_filename}")
    
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
    
    return info


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Process HSA receipt images')
    parser.add_argument('image', help='Path to receipt image')
    parser.add_argument('--output-dir', '-o', help='Output directory for receipts')
    parser.add_argument('--csv', '-c', help='Path to CSV file')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run, no file changes')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON only')
    
    args = parser.parse_args()
    
    try:
        result = process_receipt(
            args.image,
            output_dir=args.output_dir,
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
