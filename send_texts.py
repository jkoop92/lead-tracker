#!/usr/bin/env python3
"""
send_texts.py — sends the personalized outreach text to leads, one at a time,
through your Mac's own Messages app (your real phone number, not a bulk sender).

Usage:
    python3 send_texts.py --dry-run          # preview without sending anything
    python3 send_texts.py --limit 10         # actually send, capped at 10 texts

Only sends to leads with status "New" and a phone number, spaced out by
--delay seconds, and marks each one "Texted" in leads.csv as it goes so a
re-run never double-sends. macOS only (uses the Messages app via AppleScript).
"""

import argparse
import csv
import re
import subprocess
import sys
import time

from outreach_templates import load_my_info, build_scripts, MY_INFO_PATH

SCRIPT_DIR = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
APPLESCRIPT_PATH = __import__("os").path.join(SCRIPT_DIR, "send_imessage.applescript")


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None


def load_leads(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    for row in rows:
        row.setdefault("status", "")
        if not row["status"].strip():
            row["status"] = "New"
    if "status" not in fieldnames:
        fieldnames = list(fieldnames) + ["status"]
    return rows, fieldnames


def save_leads(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def send_text(phone, message):
    result = subprocess.run(
        ["osascript", APPLESCRIPT_PATH, phone, message],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unknown osascript error")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--leads", default="leads.csv", help="leads CSV to read/update (default: leads.csv)")
    parser.add_argument("--limit", type=int, default=15, help="max texts to send this run (default: 15)")
    parser.add_argument("--delay", type=float, default=8.0, help="seconds between sends (default: 8)")
    parser.add_argument("--dry-run", action="store_true", help="preview messages without sending or changing leads.csv")
    args = parser.parse_args()

    my_info = load_my_info(MY_INFO_PATH)

    try:
        rows, fieldnames = load_leads(args.leads)
    except FileNotFoundError:
        print(f"[error] {args.leads} not found. Run leadfinder.py first.", file=sys.stderr)
        sys.exit(1)

    targets = []
    for row in rows:
        if row["status"].strip().lower() != "new":
            continue
        phone = normalize_phone(row.get("phone", ""))
        if not phone:
            continue
        targets.append((row, phone))

    targets = targets[: args.limit]

    if not targets:
        print("No leads with status 'New' and a usable phone number. Nothing to do.")
        return

    print(f"{len(targets)} text(s) queued (of {sum(1 for r in rows if r['status'].strip().lower() == 'new')} eligible leads).\n")

    for row, phone in targets:
        scripts = build_scripts(row, my_info)
        print(f"To: {row.get('business_name', '')} ({phone})")
        print(f"    {scripts['text']}\n")

    if args.dry_run:
        print("[dry run] Nothing was sent, and leads.csv was not changed.")
        return

    confirm = input(f"Send these {len(targets)} text(s) now, {args.delay}s apart? Type 'yes' to continue: ")
    if confirm.strip().lower() != "yes":
        print("Cancelled. Nothing was sent.")
        return

    sent, failed = 0, 0
    for i, (row, phone) in enumerate(targets, 1):
        scripts = build_scripts(row, my_info)
        try:
            send_text(phone, scripts["text"])
            row["status"] = "Texted"
            sent += 1
            print(f"[{i}/{len(targets)}] sent to {row.get('business_name', '')}")
        except Exception as e:
            row["status"] = "Text failed"
            failed += 1
            print(f"[{i}/{len(targets)}] [error] {row.get('business_name', '')}: {e}", file=sys.stderr)

        save_leads(args.leads, rows, fieldnames)

        if i < len(targets):
            time.sleep(args.delay)

    print(f"\nDone. {sent} sent, {failed} failed. {args.leads} updated.")


if __name__ == "__main__":
    main()
