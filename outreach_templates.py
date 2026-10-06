"""Shared helpers for building personalized outreach scripts from a lead row."""

import os
import sys

MY_INFO_PATH = "my_info.txt"
MY_INFO_EXAMPLE_PATH = "my_info.example.txt"

CALL_SCRIPT = (
    "Hi, is this {business_name}? My name's {my_name} — I build websites for local "
    "{trade} businesses here in {town}. I was looking at your Google listing, saw "
    "{rating_phrase}, but noticed there's no website linked, which usually means "
    "you're losing some calls to competitors who show up with one. I'd love to put "
    "together a quick free mockup for you, no strings attached — do you have a "
    "minute, or is there a better time to catch you?"
)

TEXT_SCRIPT = (
    "Hi, this is {my_name} — I help local {trade} businesses get found online. "
    "Noticed {business_name} doesn't have a website listed on Google despite "
    "{rating_phrase}. Want me to send a free quick mockup of what one could look "
    "like? No obligation. Reply STOP to opt out. - {my_phone}"
)


def load_my_info(path=MY_INFO_PATH):
    """Reads simple `key = value` lines from my_info.txt."""
    if not os.path.exists(path):
        print(
            f"[error] {path} not found. Copy {MY_INFO_EXAMPLE_PATH} to {path} and fill in "
            "your name/phone/portfolio first.",
            file=sys.stderr,
        )
        sys.exit(1)

    info = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            info[key.strip().lower()] = value.strip()

    missing = [k for k in ("name", "phone") if not info.get(k)]
    if missing:
        print(f"[error] {path} is missing: {', '.join(missing)}. Fill those in first.", file=sys.stderr)
        sys.exit(1)

    info.setdefault("portfolio", "")
    return info


def parse_trade_town(matched_query):
    """Splits a search query like 'junk removal in Bemidji, MN' into (trade, town)."""
    if " in " in matched_query:
        trade, town = matched_query.split(" in ", 1)
    else:
        trade, town = matched_query, ""
    return trade.strip(), town.strip()


def rating_phrase(lead):
    rating = lead.get("rating", "").strip()
    reviews = lead.get("review_count", "").strip()
    if rating and reviews:
        return f"a {rating}-star rating from {reviews} reviews"
    if reviews:
        return f"{reviews} reviews"
    return "good reviews"


def build_scripts(lead, my_info):
    trade, town = parse_trade_town(lead.get("matched_query", ""))
    fmt_args = {
        "business_name": lead.get("business_name", "this business"),
        "trade": trade or "local",
        "town": town or "the area",
        "rating_phrase": rating_phrase(lead),
        "my_name": my_info["name"],
        "my_phone": my_info["phone"],
        "my_portfolio": my_info.get("portfolio", ""),
    }
    return {
        "call": CALL_SCRIPT.format(**fmt_args),
        "text": TEXT_SCRIPT.format(**fmt_args),
    }
