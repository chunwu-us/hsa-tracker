#!/usr/bin/env python3
"""
Generate HSA expense reports and summaries.
"""

import argparse
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def load_expenses(csv_path: str) -> list[dict]:
    """Load expenses from CSV."""
    expenses = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['Amount'] = float(row['Amount'])
            expenses.append(row)
    return expenses


def summarize_by_category(expenses: list[dict]) -> dict[str, float]:
    """Summarize expenses by category."""
    by_category = defaultdict(float)
    for exp in expenses:
        by_category[exp.get('Category', 'Other')] += exp['Amount']
    return dict(by_category)


def summarize_by_month(expenses: list[dict]) -> dict[str, float]:
    """Summarize expenses by month."""
    by_month = defaultdict(float)
    for exp in expenses:
        month = exp['Date'][:7]  # YYYY-MM
        by_month[month] += exp['Amount']
    return dict(sorted(by_month.items()))


def generate_report(csv_path: str = None, year: int = None) -> str:
    """Generate a text report of HSA expenses."""
    
    if year is None:
        year = datetime.now().year
    
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "data" / f"hsa_expenses_{year}.csv"
    else:
        csv_path = Path(csv_path)
    
    if not csv_path.exists():
        return f"No expense data found for {year}"
    
    expenses = load_expenses(str(csv_path))
    
    if not expenses:
        return f"No expenses recorded for {year}"
    
    # Calculate summaries
    total = sum(exp['Amount'] for exp in expenses)
    by_category = summarize_by_category(expenses)
    by_month = summarize_by_month(expenses)
    
    # Build report
    lines = [
        f"═══════════════════════════════════════════",
        f"  HSA Expense Report - {year}",
        f"═══════════════════════════════════════════",
        "",
        f"📊 SUMMARY",
        f"   Total Expenses: ${total:,.2f}",
        f"   Total Transactions: {len(expenses)}",
        "",
        f"📁 BY CATEGORY",
    ]
    
    for cat, amount in sorted(by_category.items(), key=lambda x: -x[1]):
        pct = (amount / total) * 100 if total > 0 else 0
        lines.append(f"   {cat:20} ${amount:>10,.2f}  ({pct:5.1f}%)")
    
    lines.extend([
        "",
        f"📅 BY MONTH",
    ])
    
    for month, amount in by_month.items():
        lines.append(f"   {month}              ${amount:>10,.2f}")
    
    lines.extend([
        "",
        f"📋 RECENT TRANSACTIONS",
    ])
    
    for exp in sorted(expenses, key=lambda x: x['Date'], reverse=True)[:10]:
        lines.append(f"   {exp['Date']}  {exp['Provider'][:25]:<25} ${exp['Amount']:>8,.2f}")
    
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate HSA expense report')
    parser.add_argument('--year', '-y', type=int, default=datetime.now().year, help='Report year')
    parser.add_argument('--csv', '-c', help='Path to CSV file')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    if args.json:
        import json
        csv_path = args.csv or Path(__file__).parent.parent / "data" / f"hsa_expenses_{args.year}.csv"
        if Path(csv_path).exists():
            expenses = load_expenses(str(csv_path))
            print(json.dumps({
                'year': args.year,
                'total': sum(exp['Amount'] for exp in expenses),
                'count': len(expenses),
                'by_category': summarize_by_category(expenses),
                'by_month': summarize_by_month(expenses),
                'expenses': expenses
            }, indent=2))
        else:
            print(json.dumps({'error': f'No data for {args.year}'}))
    else:
        print(generate_report(csv_path=args.csv, year=args.year))


if __name__ == '__main__':
    main()
