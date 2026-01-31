#!/usr/bin/env python3
"""
Validate HSA expense data integrity.
- Check CSV format and required fields
- Verify receipt files exist
- Check for duplicates
- Report missing receipts
"""

import argparse
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys


def validate_csv(csv_path: Path, receipts_dir: Path) -> dict:
    """Validate CSV file and check receipt references."""
    
    issues = []
    warnings = []
    stats = {
        'total_rows': 0,
        'total_amount': 0.0,
        'missing_receipts': [],
        'duplicates': [],
        'invalid_dates': [],
        'invalid_amounts': [],
    }
    
    if not csv_path.exists():
        return {'error': f'CSV not found: {csv_path}', 'issues': issues, 'warnings': warnings, 'stats': stats}
    
    seen = {}  # date+amount -> row for duplicate detection
    
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        
        # Check required columns
        required = ['Date', 'Provider', 'Amount', 'Category', 'Receipt_ID', 'Receipt_URL']
        missing_cols = [c for c in required if c not in reader.fieldnames]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        for i, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            stats['total_rows'] += 1
            
            # Validate date
            try:
                date = datetime.strptime(row['Date'], '%Y-%m-%d')
            except ValueError:
                stats['invalid_dates'].append((i, row['Date']))
                issues.append(f"Row {i}: Invalid date format '{row['Date']}'")
            
            # Validate amount
            try:
                amount = float(row['Amount'])
                stats['total_amount'] += amount
            except ValueError:
                stats['invalid_amounts'].append((i, row['Amount']))
                issues.append(f"Row {i}: Invalid amount '{row['Amount']}'")
                amount = 0
            
            # Check for duplicates
            key = f"{row['Date']}:{amount:.2f}"
            if key in seen:
                stats['duplicates'].append((i, seen[key], row['Date'], amount))
                warnings.append(f"Row {i}: Possible duplicate of row {seen[key]} ({row['Date']}, ${amount:.2f})")
            else:
                seen[key] = i
            
            # Check receipt file exists
            receipt_url = row.get('Receipt_URL', '')
            if receipt_url:
                receipt_path = receipts_dir.parent / receipt_url
                if not receipt_path.exists():
                    stats['missing_receipts'].append((i, receipt_url))
                    issues.append(f"Row {i}: Receipt not found: {receipt_url}")
    
    return {
        'csv_path': str(csv_path),
        'issues': issues,
        'warnings': warnings,
        'stats': stats,
        'valid': len(issues) == 0
    }


def validate_all(data_dir: Path = None, receipts_dir: Path = None) -> dict:
    """Validate all CSV files in data directory."""
    
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / 'data'
    if receipts_dir is None:
        receipts_dir = Path(__file__).parent.parent / 'receipts'
    
    results = {
        'files': [],
        'total_issues': 0,
        'total_warnings': 0,
        'total_amount': 0.0,
        'total_receipts': 0,
    }
    
    for csv_file in sorted(data_dir.glob('hsa_expenses_*.csv')):
        result = validate_csv(csv_file, receipts_dir)
        results['files'].append(result)
        results['total_issues'] += len(result['issues'])
        results['total_warnings'] += len(result['warnings'])
        results['total_amount'] += result['stats']['total_amount']
        results['total_receipts'] += result['stats']['total_rows']
    
    return results


def print_report(results: dict):
    """Print validation report."""
    
    print("═" * 50)
    print("  HSA Expense Validation Report")
    print("═" * 50)
    print()
    
    for file_result in results['files']:
        csv_name = Path(file_result['csv_path']).name
        status = "✅" if file_result['valid'] else "❌"
        print(f"{status} {csv_name}")
        print(f"   Rows: {file_result['stats']['total_rows']}")
        print(f"   Total: ${file_result['stats']['total_amount']:,.2f}")
        
        if file_result['issues']:
            print(f"   Issues ({len(file_result['issues'])}):")
            for issue in file_result['issues'][:5]:
                print(f"      • {issue}")
            if len(file_result['issues']) > 5:
                print(f"      • ... and {len(file_result['issues']) - 5} more")
        
        if file_result['warnings']:
            print(f"   Warnings ({len(file_result['warnings'])}):")
            for warning in file_result['warnings'][:3]:
                print(f"      ⚠ {warning}")
        print()
    
    print("─" * 50)
    print(f"Total receipts: {results['total_receipts']}")
    print(f"Total amount: ${results['total_amount']:,.2f}")
    print(f"Issues: {results['total_issues']}")
    print(f"Warnings: {results['total_warnings']}")
    print()
    
    if results['total_issues'] == 0:
        print("✅ All validations passed!")
    else:
        print("❌ Validation failed - please fix issues above")


def main():
    parser = argparse.ArgumentParser(description='Validate HSA expense data')
    parser.add_argument('--data-dir', '-d', help='Data directory containing CSVs')
    parser.add_argument('--receipts-dir', '-r', help='Receipts directory')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON')
    parser.add_argument('--year', '-y', type=int, help='Validate specific year only')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    receipts_dir = Path(args.receipts_dir) if args.receipts_dir else None
    
    if args.year:
        # Validate single year
        data_dir = data_dir or Path(__file__).parent.parent / 'data'
        receipts_dir = receipts_dir or Path(__file__).parent.parent / 'receipts'
        csv_path = data_dir / f'hsa_expenses_{args.year}.csv'
        result = validate_csv(csv_path, receipts_dir)
        
        if args.json:
            import json
            print(json.dumps(result, indent=2, default=str))
        else:
            results = {'files': [result], 'total_issues': len(result['issues']),
                      'total_warnings': len(result['warnings']), 
                      'total_amount': result['stats']['total_amount'],
                      'total_receipts': result['stats']['total_rows']}
            print_report(results)
    else:
        # Validate all
        results = validate_all(data_dir, receipts_dir)
        
        if args.json:
            import json
            print(json.dumps(results, indent=2, default=str))
        else:
            print_report(results)
    
    # Exit with error code if issues found
    sys.exit(1 if results.get('total_issues', 0) > 0 else 0)


if __name__ == '__main__':
    main()
