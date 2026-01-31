# HSA Tracker 🏥

A simple, privacy-focused HSA (Health Savings Account) expense tracker with AI-powered receipt processing.

## Features

- 📸 **AI Receipt Processing** — Extract date, provider, and amount from receipt images/PDFs using Claude Vision
- 📊 **Expense Tracking** — CSV-based storage, easy to audit and export
- 📁 **Year-Based Archive** — Receipts organized by year for 15-year IRS retention
- 🏷️ **Auto-categorization** — Medical, Dental, Vision, Prescription, Mental Health
- 📈 **Reports** — YTD summaries by category and month
- ✅ **Validation** — Check data integrity and missing receipts
- 🔄 **Batch Processing** — Process multiple receipts at once

## Quick Start

### Prerequisites

```bash
# Python 3.10+
pip install -r requirements.txt

# Set your API key (for standalone script usage)
export ANTHROPIC_API_KEY="sk-..."
```

### Process a Receipt

```bash
# Process a single receipt (image or PDF)
python scripts/process_receipt.py /path/to/receipt.pdf

# Dry run (preview without saving)
python scripts/process_receipt.py receipt.png --dry-run

# Output JSON
python scripts/process_receipt.py receipt.png --json
```

### Batch Process

```bash
# Process all receipts in a folder
python scripts/batch_process.py /path/to/incoming --processed /path/to/done

# Dry run
python scripts/batch_process.py /path/to/incoming --dry-run
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

### Validate Data

```bash
# Validate all years
python scripts/validate.py

# Validate specific year
python scripts/validate.py --year 2026

# JSON output
python scripts/validate.py --json
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
├── receipts/                       # PERMANENT ARCHIVE (gitignored)
│   ├── 2026/                       # Year-based folders
│   ├── 2027/                       # For 15-year IRS retention
│   └── ...
├── scripts/
│   ├── process_receipt.py         # AI receipt extraction
│   ├── batch_process.py           # Batch processing
│   ├── add_expense.py             # Manual entry CLI
│   ├── validate.py                # Data validation
│   └── report.py                  # Generate reports
├── config/
│   └── categories.json            # Category definitions
├── requirements.txt
└── README.md
```

## Receipt Retention

HSA receipts must be kept for potential IRS audit. Strategy:
- **Primary archive**: `receipts/YYYY/` (15+ years)
- **Backup**: Consider external drive or cloud backup
- **Index**: CSV files serve as searchable ledger

## CSV Format

```csv
Date,Provider,Amount,Category,Receipt_ID,Receipt_URL,Notes,Source
2026-01-09,Plainsboro Medical,106.38,Medical,HSA1234567890,receipts/2026/2026-01-09_plainsboro.pdf,Office visit,scan
```

## Workflows

### Automated (via Molt AI assistant)

1. Drop receipt in iCloud `Molt/hsa/incoming/`
2. Molt detects during heartbeat check
3. Extracts info via Claude Vision
4. Archives to `receipts/YYYY/`
5. Updates CSV
6. Moves original to `hsa/processed/`
7. Confirms via iMessage

### Manual (CLI)

1. Run `process_receipt.py` on receipt file
2. Script extracts info, archives, updates CSV

### Batch

1. Collect receipts in a folder
2. Run `batch_process.py` on the folder
3. All receipts processed and moved

## Privacy

- **Receipts are gitignored** — receipt images stay local only
- **Data is gitignored** — CSV expense records stay local only
- **No cloud sync of sensitive data** — only code and config tracked
- **API calls** — receipt images sent to Claude for extraction only (no storage)

## Receipt ID Generation

Each receipt gets a deterministic ID:
```
HSA + SHA256(date:provider:amount)[:10]
```

This allows deduplication while maintaining consistency.

## Categories

| Category | Description |
|----------|-------------|
| Medical | Doctor visits, hospital, urgent care, lab work |
| Dental | Dental checkups, procedures, orthodontics |
| Vision | Eye exams, glasses, contacts |
| Prescription | Prescription medications |
| Mental Health | Therapy, counseling, psychiatry |
| Other | Other HSA-eligible expenses |

## License

MIT

## Author

Built with [Claude](https://claude.ai) 🧬
