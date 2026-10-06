#!/usr/bin/env python3
"""
leadfinder.py — find businesses on Google Maps that have no website listed.

Usage:
    export GOOGLE_MAPS_API_KEY="your-key-here"
    python leadfinder.py --query "plumbers in Austin, TX" --output leads.csv

    # Multiple searches at once (one query per line in a text file)
    python leadfinder.py --queries-file queries.txt --output leads.csv --append
"""

import argparse
import csv
import os
import sys
import time
import urllib.request
import urllib.error
import json

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.googleMapsUri",
    "places.types",
    "places.businessStatus",
    "nextPageToken",
])

CSV_COLUMNS = [
    "business_name",
    "address",
    "phone",
    "rating",
    "review_count",
    "types",
    "google_maps_url",
    "place_id",
    "matched_query",
]


def api_request(url, api_key, body, field_mask, max_retries=5):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-Api-Key", api_key)
    req.add_header("X-Goog-FieldMask", field_mask)

    backoff = 2
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                print(f"  [warn] HTTP {e.code}, retrying in {backoff}s...", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"  [error] HTTP {e.code}: {body_text}", file=sys.stderr)
            raise
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                print(f"  [warn] network error ({e}), retrying in {backoff}s...", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    raise RuntimeError("exhausted retries")


def search_query(query, api_key, max_results, delay):
    """Runs a Text Search query and pages through results, up to max_results."""
    results = []
    page_token = None

    while len(results) < max_results:
        body = {"textQuery": query, "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token
        data = api_request(SEARCH_URL, api_key, body, FIELD_MASK)

        places = data.get("places", [])
        results.extend(places)

        page_token = data.get("nextPageToken")
        if not page_token or not places:
            break

        # Google requires a short delay before a new pageToken becomes valid.
        time.sleep(max(delay, 2))

    return results[:max_results]


def has_no_website(place):
    return "websiteUri" not in place or not place["websiteUri"]


def to_row(place, query):
    name = place.get("displayName", {}).get("text", "")
    phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber") or ""
    return {
        "business_name": name,
        "address": place.get("formattedAddress", ""),
        "phone": phone,
        "rating": place.get("rating", ""),
        "review_count": place.get("userRatingCount", ""),
        "types": "|".join(place.get("types", [])),
        "google_maps_url": place.get("googleMapsUri", ""),
        "place_id": place.get("id", ""),
        "matched_query": query,
    }


def load_existing_place_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["place_id"] for row in reader if row.get("place_id")}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", action="append", default=[], help='e.g. "roofers in Boise, ID" (repeatable)')
    parser.add_argument("--queries-file", help="text file with one search query per line")
    parser.add_argument("--output", default="leads.csv", help="CSV output path (default: leads.csv)")
    parser.add_argument("--append", action="store_true", help="append new leads to an existing CSV, skipping duplicates by place_id")
    parser.add_argument("--max-results", type=int, default=60, help="max results per query, capped at 60 by the API (default: 60)")
    parser.add_argument("--min-reviews", type=int, default=0, help="skip businesses with fewer than this many reviews (helps filter out closed/inactive listings)")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds to wait between paginated API calls (default: 2)")
    parser.add_argument("--api-key", default=os.environ.get("GOOGLE_MAPS_API_KEY"), help="Google Maps API key (defaults to GOOGLE_MAPS_API_KEY env var)")
    args = parser.parse_args()

    if not args.api_key:
        parser.error("no API key found. Set GOOGLE_MAPS_API_KEY or pass --api-key. See README.md for setup steps.")

    queries = list(args.query)
    if args.queries_file:
        with open(args.queries_file, encoding="utf-8") as f:
            queries.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))

    if not queries:
        parser.error("provide at least one --query or a --queries-file")

    seen_place_ids = load_existing_place_ids(args.output) if args.append else set()
    write_header = not (args.append and os.path.exists(args.output))

    mode = "a" if args.append else "w"
    total_found = 0
    total_leads = 0

    with open(args.output, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()

        for query in queries:
            print(f"Searching: {query}")
            try:
                places = search_query(query, args.api_key, args.max_results, args.delay)
            except Exception as e:
                print(f"  [error] skipping query after failure: {e}", file=sys.stderr)
                continue

            total_found += len(places)
            new_leads = 0

            for place in places:
                if not has_no_website(place):
                    continue
                if place.get("userRatingCount", 0) < args.min_reviews:
                    continue
                place_id = place.get("id", "")
                if place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)

                writer.writerow(to_row(place, query))
                new_leads += 1

            total_leads += new_leads
            print(f"  {len(places)} businesses found, {new_leads} with no website listed")

            time.sleep(args.delay)

    print(f"\nDone. {total_found} businesses scanned, {total_leads} leads with no website saved to {args.output}")


if __name__ == "__main__":
    main()
