# Quickstart

Daily commands, copy/paste ready. Run these from Terminal.

```bash
cd ~/Desktop/lead-tracker
```

## Find new leads

Edit `queries.txt` first with your target trades/cities, then:

```bash
python3 leadfinder.py --queries-file queries.txt --output leads.csv --append
```

## Build today's call sheet

```bash
python3 worklist.py
open worklist.txt
```

## Update progress

After working some calls, open the CSV and update each lead's `status`
column (`Called`, `Replied`, `Closed`, `Not Interested`, etc.):

```bash
open leads.csv
```

## Text your New leads (optional, macOS only)

Always dry-run first to preview:

```bash
python3 send_texts.py --dry-run
python3 send_texts.py --limit 10
```

See `README.md` for full setup and option details.
