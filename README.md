# Maps Lead Finder

Finds businesses on Google Maps that have **no website listed** — good
prospects for a web design/development side hustle. Searches a location +
category (e.g. "roofers in Boise, ID") via the Google Places API and writes
the ones without a website to a CSV with name, address, phone, rating, and
a Google Maps link, ready to call or email.

No third-party dependencies — just Python 3.8+ and the standard library.

## 1. Get a Google Maps API key

The Places API isn't free, but Google gives new Cloud accounts $200/month
of usage credit (as of writing), which covers thousands of searches for
this kind of use. Steps:

1. Go to https://console.cloud.google.com/ and sign in (or create an account).
2. Create a new project (top bar → "New Project"). Any name is fine, e.g. `lead-finder`.
3. Enable billing for the project: **Billing** in the left sidebar → link a
   card. You will not be charged unless you exceed the free monthly credit.
4. Enable the API: go to **APIs & Services → Library**, search for
   **"Places API (New)"**, and click **Enable**.
5. Create a key: **APIs & Services → Credentials → Create Credentials →
   API key**. Copy the key.
6. (Recommended) Restrict the key so it can't be abused if leaked:
   on the key's edit page, under **API restrictions**, choose "Restrict key"
   and select only **Places API (New)**.

Set the key as an environment variable so you don't have to pass it on the
command line every time:

```bash
export GOOGLE_MAPS_API_KEY="your-key-here"
```

Add that line to your shell profile (`~/.zshrc`, `~/.bashrc`) to persist it.

### Cost

Text Search (New) is billed per request, roughly $0.032 per call as of
writing (check https://mapsplatform.google.com/pricing/ for current
pricing). Each call returns up to 20 results, and the script pages up to 3
calls (60 results) per query. A run of 10 queries is about 10–30 API calls,
well inside the monthly free credit for normal prospecting volumes.

## 2. Run it

Single search:

```bash
python3 leadfinder.py --query "roofers in Boise, ID" --output leads.csv
```

Multiple searches in one run (see `queries.example.txt` for the format —
copy it to `queries.txt` and edit it):

```bash
cp queries.example.txt queries.txt
# edit queries.txt with your own categories/cities
python3 leadfinder.py --queries-file queries.txt --output leads.csv
```

Run it again later and only append new leads you haven't seen yet
(dedupes by Google's place ID):

```bash
python3 leadfinder.py --queries-file queries.txt --output leads.csv --append
```

### Useful options

| Flag | What it does |
|---|---|
| `--query "..."` | A single search; repeat the flag for more than one |
| `--queries-file FILE` | Run every line in a text file as a search |
| `--output FILE` | CSV output path (default `leads.csv`) |
| `--append` | Add to an existing CSV instead of overwriting, skipping duplicates |
| `--min-reviews N` | Skip businesses with fewer than N reviews (filters out closed/inactive listings) |
| `--max-results N` | Cap results per query (default 60, the API's max per query) |
| `--delay N` | Seconds between API calls (default 2) |

## 3. Output

`leads.csv` has one row per business with no website listed:

`business_name, address, phone, rating, review_count, types, google_maps_url, place_id, matched_query`

## Notes / caveats

- "No website listed" means Google's Business Profile for that listing has
  no website field filled in — the most reliable, cheap signal available
  from the API. It's not a 100% guarantee the business has zero web
  presence (some only list a Facebook/Instagram page), so it's worth a
  quick glance at the Maps link before reaching out, not a hard filter.
- Respect do-not-call/anti-spam rules in your area when using this list for
  outreach (e.g. don't robo-text; check local regulations for cold calling
  businesses).
- Re-running the same query will return the same businesses — use
  `--append` for periodic prospecting runs so you only see new leads.
