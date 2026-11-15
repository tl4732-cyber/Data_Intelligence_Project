import json
import re
import time
from datetime import datetime, timezone

import requests
from tqdm.auto import tqdm

from . import config

BASE = "https://npiregistry.cms.hhs.gov/api/"
PAGE = 200
MAX_SKIP = 1000
MANHATTAN_ZIPS = [f"{z:05d}" for z in range(10001, 10283)]
QUERY = {"version": "2.1", "state": "NY", "taxonomy_description": "Dermatology",
         "address_purpose": "LOCATION", "limit": PAGE}


def _get(session, params, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(BASE, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("Errors"):
                raise RuntimeError(f"NPPES error {data['Errors']} for {params}")
            return data
        except (requests.RequestException, ValueError):
            time.sleep(2 ** attempt)
    raise RuntimeError(f"NPPES request failed after {retries} tries: {params}")


def fetch_zip(zip5, session):
    out, skip = [], 0
    while skip <= MAX_SKIP:
        res = _get(session, {**QUERY, "postal_code": zip5, "skip": skip}).get("results", [])
        out += res
        if len(res) < PAGE:
            return out
        skip += PAGE
        time.sleep(0.3)
    print(f"WARNING: ZIP {zip5} hit the 1,200-record API cap; results may be truncated")
    return out


def load_or_fetch(cache_path=None, refresh=False):
    cache_path = cache_path or config.RAW / "raw_nppes.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text())

    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    records, per_zip = {}, {}
    for z in tqdm(MANHATTAN_ZIPS, desc="NPPES ZIPs"):
        res = fetch_zip(z, session)
        per_zip[z] = len(res)
        for rec in res:
            records[rec["number"]] = rec
        time.sleep(0.2)

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "query": QUERY,
        "zips_queried": MANHATTAN_ZIPS,
        "per_zip_counts": per_zip,
        "results": list(records.values()),
    }
    cache_path.write_text(json.dumps(payload))
    return payload


def _digits(s):
    return re.sub(r"\D", "", s or "")


def flatten(rec):
    b = rec.get("basic", {})
    loc = next((a for a in rec.get("addresses", []) if a.get("address_purpose") == "LOCATION"), {})
    taxes = rec.get("taxonomies", [])
    primary = next((t for t in taxes if t.get("primary")), taxes[0] if taxes else {})
    dba = next((o.get("organization_name") for o in rec.get("other_names", [])
                if o.get("type") == "Doing Business As"), None)
    is_org = rec.get("enumeration_type") == "NPI-2"
    person = " ".join(filter(None, [b.get("first_name"), b.get("middle_name"), b.get("last_name")]))

    return {
        "npi": rec["number"],
        "enum_type": rec["enumeration_type"],
        "name": b.get("organization_name") if is_org else person,
        "credential": b.get("credential"),
        "org_name": b.get("organization_name"),
        "dba": dba,
        "street_raw": " ".join(filter(None, [loc.get("address_1"), loc.get("address_2")])),
        "city": loc.get("city"),
        "zip5": (loc.get("postal_code") or "")[:5],
        "phone": _digits(loc.get("telephone_number"))[-10:] or None,
        "taxonomy_code": primary.get("code"),
        "taxonomy_desc": primary.get("desc"),
        "all_taxonomy_codes": "|".join(t.get("code", "") for t in taxes),
        "sole_proprietor": b.get("sole_proprietor"),
        "auth_official_first": b.get("authorized_official_first_name"),
        "auth_official_last": b.get("authorized_official_last_name"),
        "auth_official_title": b.get("authorized_official_title_or_position"),
        "auth_official_phone": _digits(b.get("authorized_official_telephone_number"))[-10:] or None,
        "parent_org": b.get("parent_organization_lbn"),
        "is_subpart": b.get("organizational_subpart"),
        "n_secondary_locations": len(rec.get("practiceLocations", [])),
        "status": b.get("status"),
        "enumeration_date": b.get("enumeration_date"),
        "last_updated": b.get("last_updated"),
    }