#!/usr/bin/env python3
"""
Manually add an HSA expense to the tracker.
"""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime
import hashlib


def generate_receipt_id(date: str, provider: str, amount: float) -> str:
    """Generate deterministic receipt ID."""
    seed = f"{date}:{provider}:{amount}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest()[:10].upper()
    return f"MED{hash_val}"


def add_expense(
    date: str,
    provider: str,
    amount: float,
    category: str = "Medical",
    notes: str = "",
    receipt_path: str = "",
    source: str = "manual",
    csv_path: str = None
) -> dict:
    """Add an expense to the CSV."""
    
    # Validate date format
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date}. Use YYYY-MM-DD")
    
    # Set default CSV path
    if csv_path is None:
        year = parsed_date.year
        csv_path = Path(__file__).parent.parent / "data" / f"hsa_expenses_{year}.csv"
    else:
        csv_path = Path(csv_path)
    
    # Generate receipt ID
    receipt_id = generate_receipt_id(date, provider, amount)
    
    # Ensure directory exists
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file exists (for header)
    file_exists = csv_path.exists()
    
    # Append to CSV
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Date', 'Provider', 'Amount', 'Category', 'Receipt_ID', 'Receipt_URL', 'Notes', 'Source'])
        writer.writerow([
            date,
            provider,
            amount,
            category,
            receipt_id,
            receipt_path,
            notes,
            source
        ])
    
    expense = {
        'date': date,
        'provider': provider,
        'amount': amount,
        'category': category,
        'receipt_id': receipt_id,
        'receipt_path': receipt_path,
        'notes': notes,
        'source': source
    }
    
    print(f"✅ Added expense:")
    print(f"   Date: {date}")
    print(f"   Provider: {provider}")
    print(f"   Amount: ${amount:.2f}")
    print(f"   Category: {category}")
    print(f"   Receipt ID: {receipt_id}")
    
    return expense


def main():
    parser = argparse.ArgumentParser(description='Add HSA expense manually')
    parser.add_argument('--date', '-d', required=True, help='Date of service (YYYY-MM-DD)')
    parser.add_argument('--provider', '-p', required=True, help='Provider name')
    parser.add_argument('--amount', '-a', required=True, type=float, help='Amount paid')
    parser.add_argument('--category', '-c', default='Medical',
                        choices=['Medical', 'Dental', 'Vision', 'Prescription', 'Mental Health', 'Other'],
                        help='Expense category')
    parser.add_argument('--notes', '-n', default='', help='Additional notes')
    parser.add_argument('--receipt', '-r', default='', help='Path to receipt file')
    parser.add_argument('--csv', help='Path to CSV file (default: data/hsa_expenses_YYYY.csv)')
    
    args = parser.parse_args()
    
    try:
        add_expense(
            date=args.date,
            provider=args.provider,
            amount=args.amount,
            category=args.category,
            notes=args.notes,
            receipt_path=args.receipt,
            csv_path=args.csv
        )
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
