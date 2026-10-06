#!/usr/bin/env python3
"""
worklist.py — turns leads.csv into a prioritized, ready-to-work call sheet.

Usage:
    python3 worklist.py --leads leads.csv --output worklist.txt

Sorts leads with the most reviews first (more established businesses =
more likely to have budget), skips anything already marked Closed or Not
Interested, and fills in a personalized call script and text script for
each one using my_info.txt.
"""

import argparse
import csv
import sys

from outreach_templates import load_my_info, build_scripts, MY_INFO_PATH

SKIP_STATUSES = {"closed", "not interested"}


def load_leads(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        row.setdefault("status", "")
        if not row["status"].strip():
            row["status"] = "New"
    return rows


def sort_key(row):
    try:
        reviews = int(row.get("review_count") or 0)
    except ValueError:
        reviews = 0
    try:
        rating = float(row.get("rating") or 0)
    except ValueError:
        rating = 0.0
    return (-reviews, -rating)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--leads", default="leads.csv", help="input CSV from leadfinder.py (default: leads.csv)")
    parser.add_argument("--output", default="worklist.txt", help="output worklist path (default: worklist.txt)")
    args = parser.parse_args()

    try:
        rows = load_leads(args.leads)
    except FileNotFoundError:
        print(f"[error] {args.leads} not found. Run leadfinder.py first.", file=sys.stderr)
        sys.exit(1)

    my_info = load_my_info(MY_INFO_PATH)

    active = [r for r in rows if r["status"].strip().lower() not in SKIP_STATUSES]
    active.sort(key=sort_key)

    with open(args.output, "w", encoding="utf-8") as out:
        out.write(f"OUTREACH WORKLIST — {len(active)} leads to work\n")
        out.write("=" * 60 + "\n\n")

        for i, lead in enumerate(active, 1):
            scripts = build_scripts(lead, my_info)
            out.write(f"[{i}] {lead.get('business_name', '')}  (status: {lead['status']})\n")
            out.write(f"    Phone: {lead.get('phone', 'none listed')}\n")
            out.write(f"    Address: {lead.get('address', '')}\n")
            out.write(f"    Rating: {lead.get('rating', '?')} stars, {lead.get('review_count', '?')} reviews\n")
            out.write(f"    Maps: {lead.get('google_maps_url', '')}\n")
            out.write("\n    CALL SCRIPT:\n")
            out.write(f"    {scripts['call']}\n")
            out.write("\n    TEXT SCRIPT:\n")
            out.write(f"    {scripts['text']}\n")
            out.write("\n" + "-" * 60 + "\n\n")

    print(f"Wrote {len(active)} leads to {args.output}")
    print(f"({len(rows) - len(active)} skipped — already Closed or Not Interested)")
    print(f"\nAfter each call, update the 'status' column in {args.leads} "
          f"(open it in Numbers/Excel) so re-running this stays accurate.")


if __name__ == "__main__":
    main()
