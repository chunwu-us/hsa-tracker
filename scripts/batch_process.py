#!/usr/bin/env python3
"""
Batch process all receipts in an incoming folder.
Useful for processing multiple receipts at once.
"""

import argparse
from pathlib import Path
import sys

from process_receipt import process_receipt


SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


def batch_process(
    incoming_dir: str,
    processed_dir: str = None,
    archive_dir: str = None,
    dry_run: bool = False,
    delete_after: bool = False
) -> dict:
    """Process all receipts in incoming directory."""
    
    incoming_dir = Path(incoming_dir)
    if not incoming_dir.exists():
        print(f"❌ Incoming directory not found: {incoming_dir}")
        return {'error': 'Directory not found'}
    
    if processed_dir:
        processed_dir = Path(processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'processed': [],
        'skipped': [],
        'errors': [],
        'duplicates': [],
    }
    
    files = [f for f in incoming_dir.iterdir() 
             if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    
    if not files:
        print(f"📭 No receipts found in {incoming_dir}")
        return results
    
    print(f"📬 Found {len(files)} receipt(s) to process\n")
    
    for receipt_file in sorted(files):
        print(f"{'─' * 40}")
        try:
            info = process_receipt(
                str(receipt_file),
                archive_dir=archive_dir,
                dry_run=dry_run
            )
            
            if info.get('duplicate'):
                results['duplicates'].append(str(receipt_file))
                action = "Would skip" if dry_run else "Skipped"
                print(f"   {action} (duplicate)")
            elif info.get('date') is None:
                results['skipped'].append(str(receipt_file))
                print(f"   ⚠️  Skipped (missing data)")
            else:
                results['processed'].append({
                    'file': str(receipt_file),
                    'info': info
                })
                
                # Move to processed or delete
                if not dry_run:
                    if processed_dir:
                        dest = processed_dir / receipt_file.name
                        receipt_file.rename(dest)
                        print(f"   📁 Moved to processed/")
                    elif delete_after:
                        receipt_file.unlink()
                        print(f"   🗑️  Deleted original")
                        
        except Exception as e:
            results['errors'].append({
                'file': str(receipt_file),
                'error': str(e)
            })
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Summary
    print("═" * 40)
    print("BATCH PROCESSING SUMMARY")
    print("═" * 40)
    print(f"✅ Processed: {len(results['processed'])}")
    print(f"⏭️  Duplicates: {len(results['duplicates'])}")
    print(f"⚠️  Skipped: {len(results['skipped'])}")
    print(f"❌ Errors: {len(results['errors'])}")
    
    if results['processed']:
        total = sum(r['info'].get('amount', 0) for r in results['processed'])
        print(f"💰 Total amount: ${total:,.2f}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Batch process HSA receipts')
    parser.add_argument('incoming', help='Directory containing receipts to process')
    parser.add_argument('--processed', '-p', help='Directory to move processed receipts')
    parser.add_argument('--archive', '-a', help='Archive directory for receipts')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run, no changes')
    parser.add_argument('--delete', '-d', action='store_true', help='Delete originals after processing')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    results = batch_process(
        args.incoming,
        processed_dir=args.processed,
        archive_dir=args.archive,
        dry_run=args.dry_run,
        delete_after=args.delete
    )
    
    if args.json:
        import json
        print(json.dumps(results, indent=2, default=str))
    
    # Exit with error if any failures
    sys.exit(1 if results.get('errors') else 0)


if __name__ == '__main__':
    main()
