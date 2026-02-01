#!/usr/bin/env python3
"""
Monitor iCloud email for HSA receipts via Mail.app AppleScript.
Extracts attachments from emails with "HSA" in subject.
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import hashlib


def run_applescript(script: str) -> str:
    """Run AppleScript and return output."""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr}")
    return result.stdout.strip()


def get_hsa_emails(account: str = "iCloud", days_back: int = 7) -> list[dict]:
    """Get emails with HSA in subject from specified account."""
    
    # AppleScript to search for HSA emails
    script = f'''
    tell application "Mail"
        set hsaMessages to {{}}
        set targetDate to (current date) - ({days_back} * days)
        
        try
            set theAccount to account "{account}"
            repeat with theMailbox in mailboxes of theAccount
                try
                    set matchingMessages to (messages of theMailbox whose subject contains "HSA" and date received > targetDate)
                    repeat with msg in matchingMessages
                        set msgId to id of msg
                        set msgSubject to subject of msg
                        set msgDate to date received of msg
                        set msgSender to sender of msg
                        set attachCount to count of mail attachments of msg
                        set end of hsaMessages to {{id:msgId, subject:msgSubject, dateStr:(msgDate as string), sender:msgSender, attachments:attachCount}}
                    end repeat
                end try
            end repeat
        end try
        
        return hsaMessages
    end tell
    '''
    
    try:
        result = run_applescript(script)
        # Parse AppleScript list output
        if not result or result == "{}":
            return []
        
        # AppleScript returns records in a specific format, parse it
        emails = []
        # Simple parsing for now - just check if we got results
        if "id:" in result:
            # Has results - return indicator for now
            return [{"raw": result}]
        return []
    except Exception as e:
        print(f"Error searching emails: {e}")
        return []


def save_attachment(message_id: int, attachment_index: int, output_dir: Path, account: str = "iCloud") -> str:
    """Save email attachment to output directory."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    script = f'''
    tell application "Mail"
        set theAccount to account "{account}"
        repeat with theMailbox in mailboxes of theAccount
            try
                set theMessages to (messages of theMailbox whose id is {message_id})
                if (count of theMessages) > 0 then
                    set theMessage to item 1 of theMessages
                    set theAttachment to mail attachment {attachment_index} of theMessage
                    set attachName to name of theAttachment
                    set attachPath to "{output_dir}/" & attachName
                    save theAttachment in POSIX file attachPath
                    return attachPath
                end if
            end try
        end repeat
        return ""
    end tell
    '''
    
    return run_applescript(script)


def get_unprocessed_emails(
    account: str = "iCloud",
    days_back: int = 7,
    processed_file: Path = None
) -> list[dict]:
    """Get HSA emails that haven't been processed yet."""
    
    if processed_file is None:
        processed_file = Path(__file__).parent.parent.parent / "memory" / "hsa-processed.json"
    
    # Load processed email IDs
    processed_ids = set()
    if processed_file.exists():
        with open(processed_file) as f:
            data = json.load(f)
            processed_ids = set(data.get('processedEmails', []))
    
    # Get HSA emails
    all_emails = get_hsa_emails(account, days_back)
    
    # Filter out processed
    unprocessed = [e for e in all_emails if e.get('id') not in processed_ids]
    
    return unprocessed


def mark_email_processed(email_id: int, processed_file: Path = None):
    """Mark an email as processed."""
    
    if processed_file is None:
        processed_file = Path(__file__).parent.parent.parent / "memory" / "hsa-processed.json"
    
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {'processedFiles': [], 'processedEmails': []}
    if processed_file.exists():
        with open(processed_file) as f:
            data = json.load(f)
    
    if email_id not in data.get('processedEmails', []):
        data.setdefault('processedEmails', []).append(email_id)
    
    with open(processed_file, 'w') as f:
        json.dump(data, f, indent=2)


def check_for_hsa_emails(
    account: str = "iCloud",
    output_dir: str = None,
    days_back: int = 7,
    dry_run: bool = False
) -> dict:
    """
    Check for HSA emails and extract attachments.
    
    Returns dict with found emails and extracted attachments.
    """
    
    if output_dir is None:
        output_dir = Path("/Volumes/My Shared Files/hsa/incoming")
    else:
        output_dir = Path(output_dir)
    
    results = {
        'checked_at': datetime.now().isoformat(),
        'account': account,
        'emails_found': 0,
        'attachments_saved': [],
        'errors': []
    }
    
    print(f"📧 Checking {account} for HSA emails (last {days_back} days)...")
    
    try:
        emails = get_hsa_emails(account, days_back)
        results['emails_found'] = len(emails)
        
        if not emails:
            print("   No new HSA emails found")
            return results
        
        print(f"   Found {len(emails)} HSA email(s)")
        
        # For now, just report what we found
        # Full attachment extraction requires more complex AppleScript
        for email in emails:
            print(f"   • {email}")
        
    except Exception as e:
        results['errors'].append(str(e))
        print(f"   ❌ Error: {e}")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor email for HSA receipts')
    parser.add_argument('--account', '-a', default='iCloud', help='Mail account name')
    parser.add_argument('--output', '-o', help='Output directory for attachments')
    parser.add_argument('--days', '-d', type=int, default=7, help='Days to look back')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    results = check_for_hsa_emails(
        account=args.account,
        output_dir=args.output,
        days_back=args.days,
        dry_run=args.dry_run
    )
    
    if args.json:
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
