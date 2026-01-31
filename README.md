# HSA Tracker 🏥

A simple, privacy-focused HSA (Health Savings Account) expense tracker with AI-powered receipt processing.

## Features

- 📸 **AI Receipt Processing** — Extract date, provider, and amount from receipt images using Claude Vision
- 📊 **Expense Tracking** — CSV-based storage, easy to audit and export
- 📁 **Local Receipt Storage** — Receipts stay on your machine (not in git)
- 🏷️ **Auto-categorization** — Medical, Dental, Vision, Prescription, Mental Health
- 📈 **Reports** — YTD summaries by category and month

## Quick Start

### Prerequisites

```bash
# Python 3.10+
pip install anthropic

# Set your API key
export ANTHROPIC_API_KEY="sk-..."
```

### Process a Receipt

```bash
# Scan a receipt image
python scripts/process_receipt.py /path/to/receipt.png

# Dry run (preview without saving)
python scripts/process_receipt.py receipt.png --dry-run

# Output JSON
python scripts/process_receipt.py receipt.png --json
```

### Add Expense Manually

```bash
python scripts/add_expense.py \
  --date 2026-01-15 \
  --provider "CVS Pharmacy" \
  --amount 25.99 \
  --category Prescription \
  --notes "Monthly medication"
```

### Generate Report

```bash
# Current year report
python scripts/report.py

# Specific year
python scripts/report.py --year 2025

# JSON output
python scripts/report.py --json
```

## Project Structure

```
hsa-tracker/
├── data/
│   ├── hsa_expenses_2026.csv      # Current year
│   └── hsa_expenses_2011-2025.csv # Historical
├── receipts/                       # Local only (gitignored)
├── scripts/
│   ├── process_receipt.py         # AI receipt extraction
│   ├── add_expense.py             # Manual entry CLI
│   └── report.py                  # Generate reports
└── config/
    └── categories.json            # Category definitions
```

## CSV Format

```csv
Date,Provider,Amount,Category,Receipt_ID,Receipt_URL,Notes,Source
2026-01-09,Plainsboro Medical,106.38,Medical,MEDAZJ4QXK9FY,receipts/2026-01-09_plainsboro.png,"Office visit",scan
```

## Workflows

### 1. Scan Paper Receipts (iPhone)

1. Open **Files** app → tap `...` → **Scan Documents**
2. Save to a watched folder
3. Run `process_receipt.py` on the scan

### 2. Digital Receipts

1. Save receipt image/PDF locally
2. Run `process_receipt.py` on the file

### 3. Manual Entry

For receipts without images, use `add_expense.py` directly.

## Privacy

- **Receipts are gitignored** — only CSV metadata is tracked
- **No cloud sync** — all data stays local
- **API calls** — only receipt images are sent to Claude for extraction

## Receipt ID Generation

Each receipt gets a deterministic ID based on date + provider + amount:
```
MED + SHA256(date:provider:amount)[:10]
```

This allows deduplication while maintaining consistency.

## License

MIT

## Author

Built with [Claude](https://claude.ai) 🤖
