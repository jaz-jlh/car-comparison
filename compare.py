import json
import os
import re
import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

try:
    import requests
    from bs4 import BeautifulSoup
    FETCH_AVAILABLE = True
except ImportError:
    FETCH_AVAILABLE = False

st.set_page_config(page_title="Car TCO Comparison", layout="wide")

SETTINGS_FILE = "settings.json"
SETTINGS_DEFAULTS = {
    "years": 7,
    "city_mi": 2500,
    "hwy_mi": 2500,
    "discount_pct": 5.0,
    "fuel_inflation_pct": 4.0,
    "purchase_type": "Auto",
    "makes": [],
    "powertrains": [],
    "year_range": [2018, 2026],
    "max_price": None,  # filled after CSV loads
    "req_cpo": False,
    "req_hvac": False,
    "req_awd": False,
    "req_aeb": False,
    "req_acc": False,
    "min_iihs": 0,
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            s = SETTINGS_DEFAULTS.copy()
            s.update(saved)
            return s
        except Exception:
            pass
    return SETTINGS_DEFAULTS.copy()


def save_settings(s: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

MAKE_COLORS = {
    "Toyota": "#DC2626",
    "Subaru": "#2563EB",
    "Honda": "#059669",
    "Ford": "#7C3AED",
    "Mazda": "#EA580C",
    "Hyundai": "#0891B2",
    "Kia": "#D97706",
}
PT_COLORS = {"Gas": "#6366F1", "Hybrid": "#059669", "PHEV": "#F59E0B"}

LISTINGS_FILE = "listings.json"
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Listings persistence ───────────────────────────────────────────────────────

def load_listings() -> list:
    if os.path.exists(LISTINGS_FILE):
        try:
            with open(LISTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_listings(lst: list) -> None:
    with open(LISTINGS_FILE, "w") as f:
        json.dump(lst, f, indent=2, default=str)


# ── URL parsing helpers ────────────────────────────────────────────────────────

def _parse_price_str(val) -> float | None:
    if val is None:
        return None
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _parse_name_tokens(name: str) -> dict:
    """Parse '2021 Toyota RAV4 XLE' into year/make/model/trim tokens."""
    tokens = name.strip().split()
    result = {}
    if tokens and len(tokens[0]) == 4 and tokens[0].isdigit():
        result["year"] = int(tokens[0])
        if len(tokens) > 1:
            result["make"] = tokens[1]
        if len(tokens) > 2:
            result["model"] = tokens[2]
        if len(tokens) > 3:
            result["trim"] = " ".join(tokens[3:])
    return result


def _try_jsonld(soup) -> dict | None:
    """Strategy 1: JSON-LD Vehicle/Car schema (Cars.com, others)."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") not in ("Vehicle", "Car", "Product"):
                continue
            result = _parse_name_tokens(item.get("name", ""))
            # Explicit structured fields override name parsing
            if item.get("vehicleModelDate"):
                try:
                    result["year"] = int(item["vehicleModelDate"])
                except Exception:
                    pass
            brand = item.get("brand", {})
            if isinstance(brand, dict):
                result["make"] = brand.get("name") or result.get("make")
            elif isinstance(brand, str):
                result["make"] = brand
            if item.get("model"):
                result["model"] = item["model"]
            # Price
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            result["price"] = _parse_price_str(offers.get("price") or item.get("price"))
            # Mileage
            mileage = item.get("mileageFromOdometer", {})
            if isinstance(mileage, dict):
                result["mileage"] = _parse_price_str(mileage.get("value"))
            elif mileage:
                result["mileage"] = _parse_price_str(mileage)
            result["fuel_type"] = item.get("fuelType")
            if result.get("year") or result.get("price"):
                return result
    return None


def _try_next_data(soup) -> dict | None:
    """Strategy 2: Edmunds __NEXT_DATA__ (Next.js) embedded JSON."""
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        data = json.loads(tag.string)
    except Exception:
        return None

    page_props = data.get("props", {}).get("pageProps", {})
    # Try multiple known Edmunds paths
    listing = (
        page_props.get("data", {}).get("listing", {})
        or page_props.get("listing", {})
        or {}
    )
    vehicle = listing.get("vehicle", {}) or listing

    result = {}
    try:
        result["year"] = int(vehicle.get("year") or listing.get("year") or 0) or None
    except Exception:
        pass
    make = vehicle.get("make", {})
    result["make"] = make.get("name") if isinstance(make, dict) else (make or None)
    model = vehicle.get("model", {})
    result["model"] = model.get("name") if isinstance(model, dict) else (model or None)
    trim = vehicle.get("trim", {})
    result["trim"] = trim.get("name") if isinstance(trim, dict) else (trim or None)
    result["mileage"] = _parse_price_str(vehicle.get("mileage") or listing.get("mileage"))
    prices = listing.get("prices", {}) or {}
    result["price"] = _parse_price_str(
        prices.get("displayPrice") or prices.get("price") or listing.get("price")
    )
    if result.get("year") or result.get("price"):
        return result
    return None


def _try_initial_state(html_text: str) -> dict | None:
    """Strategy 2b: CarGurus window.__INITIAL_STATE__ embedded JSON."""
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+)", html_text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    end = raw.find("</script>")
    if end != -1:
        raw = raw[:end].rstrip("; \n\r")
    try:
        state = json.loads(raw)
    except Exception:
        return None
    listing = (
        state.get("listingPage", {}).get("listing", {})
        or state.get("listing", {})
        or {}
    )
    result = {}
    try:
        result["year"] = int(listing.get("year") or 0) or None
    except Exception:
        pass
    result["make"] = listing.get("make") or listing.get("makeName")
    result["model"] = listing.get("model") or listing.get("modelName")
    result["trim"] = listing.get("trim") or listing.get("trimName")
    result["price"] = _parse_price_str(listing.get("price") or listing.get("listingPrice"))
    result["mileage"] = _parse_price_str(listing.get("mileage"))
    if result.get("year") or result.get("price"):
        return result
    return None


def _try_kbb_data(soup, html_text: str) -> dict | None:
    """Strategy 2c: KBB window.__BONNET_DATA__ / dataLayer embedded JSON."""
    # Try window.__BONNET_DATA__
    m = re.search(r"window\.__BONNET_DATA__\s*=\s*(\{.+)", html_text, re.DOTALL)
    if m:
        raw = m.group(1)
        end = raw.find("</script>")
        if end != -1:
            raw = raw[:end].rstrip("; \n\r")
        try:
            data = json.loads(raw)
            listing = (
                data.get("listing", {})
                or data.get("vehicle", {})
                or {}
            )
            result = {}
            try:
                result["year"] = int(listing.get("year") or 0) or None
            except Exception:
                pass
            result["make"] = listing.get("make") or listing.get("makeName")
            result["model"] = listing.get("model") or listing.get("modelName")
            result["trim"] = listing.get("trim") or listing.get("trimName")
            result["price"] = _parse_price_str(
                listing.get("price") or listing.get("listingPrice") or listing.get("askingPrice")
            )
            result["mileage"] = _parse_price_str(listing.get("mileage"))
            if result.get("year") or result.get("price"):
                return result
        except Exception:
            pass

    # Try dataLayer (GTM/analytics — KBB populates this with vehicle info)
    for m in re.finditer(r"dataLayer\.push\s*\(\s*(\{.+?\})\s*\)", html_text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        if not any(k in data for k in ("vehicleYear", "make", "model", "listingPrice")):
            continue
        result = {}
        try:
            result["year"] = int(data.get("vehicleYear") or data.get("year") or 0) or None
        except Exception:
            pass
        result["make"] = data.get("make") or data.get("vehicleMake")
        result["model"] = data.get("model") or data.get("vehicleModel")
        result["trim"] = data.get("trim") or data.get("vehicleTrim")
        result["price"] = _parse_price_str(
            data.get("listingPrice") or data.get("price") or data.get("vehiclePrice")
        )
        result["mileage"] = _parse_price_str(data.get("mileage") or data.get("vehicleMileage"))
        if result.get("year") or result.get("price"):
            return result

    # Try KBB-specific page elements
    result = {}
    # Price
    price_tag = (
        soup.find("span", {"data-test": "vehicle-card-price"})
        or soup.find("span", class_=re.compile(r"price", re.I))
        or soup.find("div", {"data-test": "listing-price"})
    )
    if price_tag:
        result["price"] = _parse_price_str(price_tag.get_text(strip=True))
    # Title (e.g. "2020 Toyota RAV4 XLE")
    title_tag = (
        soup.find("h1", {"data-test": "vehicle-name"})
        or soup.find("h1", class_=re.compile(r"title", re.I))
        or soup.find("h1")
    )
    if title_tag:
        result.update(_parse_name_tokens(title_tag.get_text(strip=True)))
    if result.get("year") or result.get("price"):
        return result

    return None


def _parse_kbb_url_params(url: str) -> dict | None:
    """Extract make/model/year from KBB URL query parameters as a last-resort fallback."""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    if "kbb.com" not in parsed.netloc:
        return None
    params = parse_qs(parsed.query)
    result = {}
    make_code = (params.get("makeCode") or [None])[0]
    if make_code:
        result["make"] = make_code.title()  # "TOYOTA" → "Toyota"
    model_code = (params.get("modelCode") or [None])[0]
    if model_code:
        # "RAV4" stays "RAV4"; multi-word codes like "PILOT" → "Pilot"
        result["model"] = model_code.replace("-", " ")
    # endYear/startYear are search filter context — use only when both match (single year)
    end_year = (params.get("endYear") or [None])[0]
    start_year = (params.get("startYear") or [None])[0]
    if end_year and end_year == start_year:
        try:
            result["year"] = int(end_year)
        except ValueError:
            pass
    return result if (result.get("make") or result.get("model")) else None


def _try_meta_tags(soup) -> dict | None:
    """Strategy 3: Craigslist selectors and OG/meta tags."""
    result = {}
    # Craigslist
    cl_title = soup.find("span", id="titletextonly") or soup.find("h2", class_="postingtitletext")
    if cl_title:
        result.update(_parse_name_tokens(cl_title.get_text(strip=True)))
    cl_price = soup.find("span", class_="price")
    if cl_price:
        result["price"] = _parse_price_str(cl_price.get_text(strip=True))
    # OG title fallback
    og_title = soup.find("meta", property="og:title")
    if og_title and not result.get("year"):
        result.update(_parse_name_tokens(og_title.get("content", "")))
    # Price meta tags
    if not result.get("price"):
        for attr, name in [
            ("property", "product:price:amount"),
            ("name", "price"),
            ("name", "twitter:data1"),
        ]:
            tag = soup.find("meta", {attr: name})
            if tag:
                p = _parse_price_str(tag.get("content"))
                if p:
                    result["price"] = p
                    break
    return result if (result.get("year") or result.get("price")) else None


KNOWN_MAKES = [
    "Toyota", "Honda", "Ford", "Chevrolet", "Chevy", "Subaru", "Mazda",
    "Hyundai", "Kia", "Nissan", "Volkswagen", "BMW", "Mercedes", "Audi",
    "Lexus", "Acura", "Infiniti", "Volvo", "Jeep", "Ram", "GMC", "Buick",
    "Cadillac", "Lincoln", "Chrysler", "Dodge", "Mitsubishi",
]


def parse_pasted_text(text: str) -> dict:
    """
    Extract vehicle details from raw copy-pasted listing page text.
    Returns same shape as fetch_listing: year, make, model, trim, price, mileage.

    Handles KBB-style multi-line format, e.g.:
        Toyota Silver Certified
        2018 Toyota RAV4
        XLE
        113K mi
        16,995
    """
    result: dict = {k: None for k in ["year", "make", "model", "trim", "price", "mileage"]}
    lines = [l.strip() for l in text.splitlines()]
    lines_ne = [l for l in lines if l]  # non-empty

    # ── Mileage ────────────────────────────────────────────────────────────────
    # "25,432 miles" / "113K mi" / "113k miles" / "mileage: 25,432"
    mi_match = re.search(
        r"(?:mileage[:\s]+)?([\d,]+)\s*[Kk]\s*(?:miles?|mi\.?\b)"  # 113K mi
        r"|(?:mileage[:\s]+)?([\d,]+)\s*(?:miles?|mi\.?\b)",        # 25,432 mi
        text, re.IGNORECASE,
    )
    if mi_match:
        if mi_match.group(1):
            result["mileage"] = float(mi_match.group(1).replace(",", "")) * 1000
        else:
            result["mileage"] = _parse_price_str(mi_match.group(2))

    # ── Price ──────────────────────────────────────────────────────────────────
    # 1) Prefer explicit "$27,998"
    for m in re.finditer(r"\$\s*([\d,]+)", text):
        val = _parse_price_str(m.group(1))
        if val and val >= 1000:
            result["price"] = val
            break
    # 2) Bare number on its own line that looks like a price (4–6 digits, $1k–$200k),
    #    not already matched as mileage
    if not result["price"]:
        for line in lines_ne:
            m = re.fullmatch(r"([\d,]+)", line)
            if not m:
                continue
            val = _parse_price_str(m.group(1))
            if val and 1000 <= val <= 200000 and val != result.get("mileage"):
                result["price"] = val
                break

    # ── Year / Make / Model / Trim ─────────────────────────────────────────────
    makes_pattern = "|".join(re.escape(mk) for mk in KNOWN_MAKES)

    # Look for a line containing "YYYY Make Model [inline-trim]"
    ymm_re = re.compile(
        rf"\b(20\d{{2}})\s+({makes_pattern})\s+(\S+)(?:\s+(.+?))?$",
        re.IGNORECASE,
    )
    ymm_line_idx = None
    for idx, line in enumerate(lines_ne):
        m = ymm_re.search(line)
        if m:
            result["year"] = int(m.group(1))
            raw_make = m.group(2)
            result["make"] = next(
                (mk for mk in KNOWN_MAKES if mk.lower() == raw_make.lower()), raw_make.title()
            )
            result["model"] = m.group(3)
            inline_trim = (m.group(4) or "").strip().rstrip(".,|")
            if inline_trim:
                result["trim"] = inline_trim
            ymm_line_idx = idx
            break

    # If trim wasn't inline, check the next non-empty line after the YMM line
    if ymm_line_idx is not None and not result["trim"]:
        for line in lines_ne[ymm_line_idx + 1:]:
            # Accept as trim if it's short, has no digits, and isn't a known noise word
            noise = re.compile(r"\b(certified|cpo|used|new|miles?|mi|price|deal|sale)\b", re.I)
            if len(line) <= 30 and not re.search(r"\d", line) and not noise.search(line):
                result["trim"] = line
                break

    # Fallbacks if YMM line not found
    if not result["year"]:
        yr = re.search(r"\b(20[12]\d)\b", text)
        if yr:
            result["year"] = int(yr.group(1))
    if not result["make"]:
        mk = re.search(rf"\b({makes_pattern})\b", text, re.IGNORECASE)
        if mk:
            raw_make = mk.group(1)
            result["make"] = next(
                (m for m in KNOWN_MAKES if m.lower() == raw_make.lower()), raw_make.title()
            )

    filled = sum(1 for v in result.values() if v is not None)
    confidence = "parsed" if filled >= 4 else ("partial" if filled >= 2 else "failed")
    return {**result, "confidence": confidence, "source": "pasted-text", "raw_error": None}


def fetch_listing(url: str) -> dict:
    """
    Fetch a car listing URL and extract vehicle details.
    Returns dict: year, make, model, trim, price, mileage,
    confidence ('parsed'|'partial'|'failed'), source, raw_error.
    """
    empty = {k: None for k in ["year", "make", "model", "trim", "price", "mileage", "fuel_type"]}
    result = {**empty, "confidence": "failed", "source": None, "raw_error": None}

    if not FETCH_AVAILABLE:
        result["raw_error"] = "Install requests and beautifulsoup4: pip install requests beautifulsoup4"
        return result

    try:
        resp = requests.get(url, headers=FETCH_HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        result["raw_error"] = str(e)
        # For KBB, a 403 is expected — still extract what we can from the URL params
        url_params = _parse_kbb_url_params(url)
        if url_params:
            for k, v in url_params.items():
                result[k] = v
            result["source"] = "kbb-url-params"
            result["confidence"] = "partial"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    for strategy, fn in [
        ("json-ld",       lambda: _try_jsonld(soup)),
        ("next-data",     lambda: _try_next_data(soup)),
        ("initial-state", lambda: _try_initial_state(resp.text)),
        ("kbb",           lambda: _try_kbb_data(soup, resp.text)),
        ("meta",          lambda: _try_meta_tags(soup)),
    ]:
        try:
            parsed = fn()
        except Exception:
            continue
        if not parsed:
            continue
        result.update({k: v for k, v in parsed.items() if v is not None})
        result["source"] = strategy
        has_id = result.get("year") and (result.get("make") or result.get("model"))
        result["confidence"] = "parsed" if (has_id and result.get("price")) else "partial"
        if result["confidence"] == "parsed":
            return result

    # For KBB URLs, fill any missing make/model from URL query params (search-context fallback)
    url_params = _parse_kbb_url_params(url)
    if url_params:
        for k, v in url_params.items():
            if not result.get(k):
                result[k] = v
        if result["source"] is None:
            result["source"] = "kbb-url-params"
        has_id = result.get("year") and (result.get("make") or result.get("model"))
        result["confidence"] = "parsed" if (has_id and result.get("price")) else "partial"

    return result


# ── Listing matching & TCO ─────────────────────────────────────────────────────

def match_to_csv(listing: dict, df: pd.DataFrame) -> dict:
    """
    Find the best-matching CSV row for a listing.
    Returns {row: pd.Series|None, confidence: str, match_label: str}.
    """
    year = listing.get("year")
    make = (listing.get("make") or "").strip()
    model = (listing.get("model") or "").strip()
    trim = (listing.get("trim") or "").strip()
    price = listing.get("price")

    if not year or not make:
        return {"row": None, "confidence": "none", "match_label": "Need at least year and make"}

    mask = (df["Year"] == int(year)) & (df["Make"].str.lower() == make.lower())
    candidates = df[mask]
    if candidates.empty:
        return {"row": None, "confidence": "none",
                "match_label": f"No CSV entries for {year} {make}"}

    # Model matching
    if model:
        model_mask = candidates["Model"].str.lower().str.contains(model.lower(), regex=False)
        if not model_mask.any():
            for csv_model in candidates["Model"].unique():
                if csv_model.lower() in model.lower():
                    model_mask = candidates["Model"].str.lower() == csv_model.lower()
                    break
        model_candidates = candidates[model_mask] if model_mask.any() else candidates
    else:
        model_candidates = candidates

    # Trim scoring
    if trim:
        exact = model_candidates[model_candidates["Trim"].str.lower() == trim.lower()]
        if not exact.empty:
            row = exact.iloc[0]
            return {"row": row, "confidence": "exact",
                    "match_label": f"{row['Label']} (exact trim)"}
        if price:
            scored = model_candidates.copy()
            scored["_delta"] = (scored["MSRP_New_Est"] - price).abs()
            best = scored.nsmallest(1, "_delta").iloc[0]
        else:
            best = model_candidates.sort_values("MSRP_New_Est").iloc[len(model_candidates) // 2]
        return {"row": best, "confidence": "close",
                "match_label": f"{best['Label']} (closest by price — trim '{trim}' not found)"}

    best = model_candidates.sort_values("MSRP_New_Est").iloc[0]
    return {"row": best, "confidence": "model-only",
            "match_label": f"{best['Label']} (model match, no trim info)"}


def compute_listing_tco(
    matched_row: pd.Series,
    listing_price: float,
    years: int,
    city_mi: float,
    hwy_mi: float,
    discount_pct: float,
    fuel_inflation_pct: float,
    listing_mileage: float = 25000,
) -> pd.Series:
    """Compute TCO for a real listing using its actual price, inheriting model costs from CSV."""
    row_df = matched_row.to_frame().T.copy().reset_index(drop=True)
    row_df["Used_Price_Est_25K_mi"] = listing_price
    row_df["MSRP_New_Est"] = listing_price
    if "Maint_7yr" not in row_df.columns:
        row_df["Maint_7yr"] = (
            row_df["Scheduled_Maint_7yr"].fillna(0)
            + row_df["Unscheduled_Repair_7yr"].fillna(0)
        )
    # Scale maintenance by listing mileage relative to the 25K-mile CSV baseline.
    # Higher-mileage vehicles face greater wear and unscheduled repair costs.
    mileage_factor = (max(listing_mileage, 1) / 25000) ** 0.35
    row_df["Maint_7yr"] = row_df["Maint_7yr"] * mileage_factor
    result_df = compute_tco(row_df, years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct, "Auto")
    return result_df.iloc[0]


@st.cache_data
def load_data():
    df = pd.read_csv("Car Comparison - Sheet1.csv")

    for col in [
        "MSRP_New_Est",
        "Used_Price_Est_25K_mi",
        "Resale_7yr",
        "Scheduled_Maint_7yr",
        "Unscheduled_Repair_7yr",
        "Insurance_Annual",
    ]:
        df[col] = (
            df[col].astype(str).str.replace(r"[$,]", "", regex=True).str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Maint_7yr"] = df["Scheduled_Maint_7yr"].fillna(0) + df[
        "Unscheduled_Repair_7yr"
    ].fillna(0)

    df["Label"] = (
        df["Year"].astype(str)
        + " "
        + df["Make"]
        + " "
        + df["Model"]
        + " "
        + df["Trim"]
    )

    def broad_pt(p):
        if p == "PHEV":
            return "PHEV"
        if p == "Hybrid":
            return "Hybrid"
        return "Gas"

    df["Powertrain_Cat"] = df["Powertrain"].apply(broad_pt)

    def iihs_rank(r):
        if pd.isna(r):
            return 0
        r = str(r)
        if "TSP+" in r:
            return 2
        if "TSP" in r:
            return 1
        return 0

    df["IIHS_Rank"] = df["IIHS_Rating"].apply(iihs_rank)
    df["Has_Physical_HVAC"] = df["Physical_HVAC_Controls"] == "Yes"
    df["Has_AEB"] = df["AEB_Standard"] == "Yes"
    df["Has_ACC"] = df["ACC_Standard"] == "Yes"
    df["Has_AWD"] = df["AWD_Standard"] == "Yes"

    return df


def get_purchase_price(df: pd.DataFrame, purchase_type: str) -> pd.Series:
    if purchase_type == "Auto":
        return df.apply(
            lambda r: r["Used_Price_Est_25K_mi"]
            if r["Year"] <= 2024
            else r["MSRP_New_Est"],
            axis=1,
        )
    return df["MSRP_New_Est"]


def compute_tco(
    df: pd.DataFrame,
    years: int,
    city_mi: float,
    hwy_mi: float,
    discount_pct: float,
    fuel_inflation_pct: float,
    purchase_type: str,
) -> pd.DataFrame:
    r = discount_pct / 100.0
    g = fuel_inflation_pct / 100.0
    df = df.copy()

    df["Purchase"] = get_purchase_price(df, purchase_type)

    df["Annual_Fuel"] = (
        city_mi * df["Fuel_cost_city_per_mile"]
        + hwy_mi * df["Fuel_cost_hwy_per_mile"]
    )
    df["Annual_Insurance"] = df["Insurance_Annual"]
    df["Annual_Maint"] = df["Maint_7yr"] / 7.0

    pv_factor = (1 - (1 + r) ** (-years)) / r if r > 0 else float(years)
    # Growing annuity factor for fuel (gas prices inflate at rate g)
    if abs(r - g) > 1e-9:
        fuel_pv_factor = (1 - ((1 + g) / (1 + r)) ** years) / (r - g)
    elif r > 0:
        fuel_pv_factor = years / (1 + r)
    else:
        fuel_pv_factor = float(years)

    # Derive implied annual resale rate from the 7-year CSV value
    ratio = (df["Resale_7yr"] / (df["Purchase"] * 0.88)).clip(lower=0.001, upper=0.999)
    df["Implied_Rate"] = ratio ** (1.0 / 7.0)
    df["Resale_N"] = df["Purchase"] * (df["Implied_Rate"] ** years) * 0.88
    df["PV_Resale"] = df["Resale_N"] / ((1 + r) ** years)

    df["PV_Fuel"] = df["Annual_Fuel"] * fuel_pv_factor
    df["PV_Insurance"] = df["Annual_Insurance"] * pv_factor
    df["PV_Maint"] = df["Annual_Maint"] * pv_factor
    df["TCO"] = df["Purchase"] + df["PV_Fuel"] + df["PV_Insurance"] + df["PV_Maint"] - df["PV_Resale"]

    return df


def apply_filters(
    df: pd.DataFrame,
    makes: list,
    powertrains: list,
    year_range: tuple,
    max_price: int,
    req_cpo: bool,
    req_hvac: bool,
    req_awd: bool,
    req_aeb: bool,
    req_acc: bool,
    min_iihs: int,
    purchase_type: str,
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if makes:
        mask &= df["Make"].isin(makes)
    if powertrains:
        mask &= df["Powertrain_Cat"].isin(powertrains)
    mask &= df["Year"].between(year_range[0], year_range[1])
    price_series = get_purchase_price(df, purchase_type)
    mask &= price_series <= max_price
    if req_cpo:
        mask &= (df["CPO_Available"] == "Yes") | (df["Year"] > 2024)
    if req_hvac:
        mask &= df["Has_Physical_HVAC"]
    if req_awd:
        mask &= df["Has_AWD"]
    if req_aeb:
        mask &= df["Has_AEB"]
    if req_acc:
        mask &= df["Has_ACC"]
    if min_iihs > 0:
        mask &= df["IIHS_Rank"] >= min_iihs
    return df[mask].copy()


# ── Load ──────────────────────────────────────────────────────────────────────

df_raw = load_data()
s = load_settings()

# Fill max_price default from CSV if not yet saved
max_msrp = int(df_raw["MSRP_New_Est"].max())
if s["max_price"] is None:
    s["max_price"] = max_msrp

# Validate multiselect defaults against current CSV values
all_makes = sorted(df_raw["Make"].unique())
s["makes"] = [m for m in s["makes"] if m in all_makes]
s["powertrains"] = [p for p in s["powertrains"] if p in ["Gas", "Hybrid", "PHEV"]]
s["year_range"] = [
    max(2018, min(2026, s["year_range"][0])),
    max(2018, min(2026, s["year_range"][1])),
]
s["max_price"] = max(15_000, min(max_msrp, s["max_price"]))

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Parameters")
    if st.button("🔄 Reload CSV"):
        load_data.clear()
        st.rerun()

    st.subheader("Ownership")
    years = st.slider("Years of ownership", 1, 15, s["years"])
    city_mi = st.number_input(
        "Annual city miles", min_value=0, max_value=50_000, value=s["city_mi"], step=500
    )
    hwy_mi = st.number_input(
        "Annual hwy miles", min_value=0, max_value=50_000, value=s["hwy_mi"], step=500
    )
    discount_pct = st.slider("Discount rate (%)", 0.0, 10.0, s["discount_pct"], 0.5)
    fuel_inflation_pct = st.slider("Fuel price inflation (%/yr)", 0.0, 10.0, s["fuel_inflation_pct"], 0.5)
    purchase_type = st.radio(
        "Purchase type",
        ["Auto", "New (MSRP)"],
        index=["Auto", "New (MSRP)"].index(s["purchase_type"]),
        help="Auto = used price for 2018–2024, MSRP for 2025–2026",
    )

    st.divider()
    st.subheader("Filters")

    makes = st.multiselect("Make", all_makes, default=s["makes"], placeholder="All makes")
    powertrains = st.multiselect(
        "Powertrain", ["Gas", "Hybrid", "PHEV"], default=s["powertrains"], placeholder="All types"
    )
    year_range = st.slider("Model year range", 2018, 2026, tuple(s["year_range"]))
    max_price = st.slider(
        "Max purchase price", 15_000, max_msrp, s["max_price"], step=1_000, format="$%d"
    )

    st.divider()
    st.subheader("Required Features")
    req_cpo = st.toggle("CPO available", value=s["req_cpo"])
    req_hvac = st.toggle("Physical HVAC controls only", value=s["req_hvac"])
    req_awd = st.toggle("AWD standard", value=s["req_awd"])
    req_aeb = st.toggle("AEB standard", value=s["req_aeb"])
    req_acc = st.toggle("ACC standard", value=s["req_acc"])
    iihs_labels = {0: "Any", 1: "TSP or better", 2: "TSP+ only"}
    min_iihs = st.selectbox(
        "Min IIHS rating", options=[0, 1, 2], index=s["min_iihs"],
        format_func=lambda x: iihs_labels[x]
    )

    # Persist current values after every interaction
    save_settings({
        "years": years,
        "city_mi": int(city_mi),
        "hwy_mi": int(hwy_mi),
        "discount_pct": discount_pct,
        "fuel_inflation_pct": fuel_inflation_pct,
        "purchase_type": purchase_type,
        "makes": makes,
        "powertrains": powertrains,
        "year_range": list(year_range),
        "max_price": max_price,
        "req_cpo": req_cpo,
        "req_hvac": req_hvac,
        "req_awd": req_awd,
        "req_aeb": req_aeb,
        "req_acc": req_acc,
        "min_iihs": min_iihs,
    })

# ── Compute ───────────────────────────────────────────────────────────────────

df_filtered = apply_filters(
    df_raw,
    makes,
    powertrains,
    year_range,
    max_price,
    req_cpo,
    req_hvac,
    req_awd,
    req_aeb,
    req_acc,
    min_iihs,
    purchase_type,
)
df = compute_tco(df_filtered, years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct, purchase_type)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Car TCO Comparison")
st.caption(
    f"{len(df)} vehicles · {years}yr ownership · "
    f"{city_mi:,} city + {hwy_mi:,} hwy mi/yr · "
    f"{discount_pct}% discount rate"
)

if df.empty:
    st.warning("No vehicles match the current filters.")
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🏆 Rankings", "📊 Cost Breakdown", "🔵 Scatter", "📈 Sensitivity", "📋 Data Table", "📌 My Listings"]
)

# ── Tab 1: Rankings ───────────────────────────────────────────────────────────

with tab1:
    n_vehicles = len(df)
    if n_vehicles <= 1:
        top_n = n_vehicles
    else:
        top_n = st.slider(
            "Show top N vehicles by TCO",
            1,
            min(100, n_vehicles),
            min(30, n_vehicles),
            key="top_n",
        )
    df_top = df.nsmallest(top_n, "TCO").sort_values("TCO", ascending=True)

    fig1 = go.Figure()
    for make in df_top["Make"].unique():
        sub = df_top[df_top["Make"] == make]
        fig1.add_trace(
            go.Bar(
                x=sub["TCO"],
                y=sub["Label"],
                name=make,
                orientation="h",
                marker_color=MAKE_COLORS.get(make, "#888"),
                customdata=sub[
                    ["Purchase", "PV_Fuel", "PV_Insurance", "PV_Maint", "PV_Resale", "Powertrain"]
                ].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "TCO: $%{x:,.0f}<br>"
                    "─────────────<br>"
                    "Purchase: $%{customdata[0]:,.0f}<br>"
                    "Fuel (PV): $%{customdata[1]:,.0f}<br>"
                    "Insurance (PV): $%{customdata[2]:,.0f}<br>"
                    "Maintenance (PV): $%{customdata[3]:,.0f}<br>"
                    "Resale credit: −$%{customdata[4]:,.0f}<br>"
                    "Powertrain: %{customdata[5]}"
                    "<extra></extra>"
                ),
            )
        )

    # Overlay saved listings as hatched orange bars
    _saved = load_listings()
    _listing_plot_rows = []
    for _lst in _saved:
        _csv_key = _lst.get("matched_csv_key")
        if not _csv_key or not _lst.get("listing_price"):
            continue
        _csv_match = df_raw[df_raw["Label"] == _csv_key]
        if _csv_match.empty:
            continue
        _tco_row = compute_listing_tco(
            _csv_match.iloc[0], _lst["listing_price"],
            years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct,
            listing_mileage=_lst.get("mileage", 25000),
        )
        _listing_plot_rows.append({
            "label": f"★ {_lst['label']}",
            "TCO": _tco_row["TCO"],
            "Purchase": _tco_row["Purchase"],
            "PV_Fuel": _tco_row["PV_Fuel"],
            "PV_Insurance": _tco_row["PV_Insurance"],
            "PV_Maint": _tco_row["PV_Maint"],
            "PV_Resale": _tco_row["PV_Resale"],
            "Powertrain": _lst.get("powertrain", ""),
        })
    if _listing_plot_rows:
        _lst_df = pd.DataFrame(_listing_plot_rows)
        fig1.add_trace(go.Bar(
            x=_lst_df["TCO"],
            y=_lst_df["label"],
            name="My Listings",
            orientation="h",
            marker_color="#F97316",
            marker_pattern_shape="/",
            marker_pattern_fgcolor="white",
            customdata=_lst_df[
                ["Purchase", "PV_Fuel", "PV_Insurance", "PV_Maint", "PV_Resale", "Powertrain"]
            ].values,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "TCO: $%{x:,.0f}<br>"
                "─────────────<br>"
                "Purchase: $%{customdata[0]:,.0f}<br>"
                "Fuel (PV): $%{customdata[1]:,.0f}<br>"
                "Insurance (PV): $%{customdata[2]:,.0f}<br>"
                "Maintenance (PV): $%{customdata[3]:,.0f}<br>"
                "Resale credit: −$%{customdata[4]:,.0f}<br>"
                "Powertrain: %{customdata[5]}"
                "<extra></extra>"
            ),
        ))

    # Build a unified label→TCO map so listings slot into the correct rank position
    _all_tco = {row["Label"]: row["TCO"] for _, row in df_top.iterrows()}
    for _r in _listing_plot_rows:
        _all_tco[_r["label"]] = _r["TCO"]
    # categoryarray bottom→top = ascending TCO (best at bottom, worst at top)
    _category_array = sorted(_all_tco, key=_all_tco.get, reverse=True)

    fig1.update_layout(
        height=max(400, (top_n + len(_listing_plot_rows)) * 22),
        barmode="overlay",
        xaxis_title="Total Cost of Ownership ($)",
        xaxis_tickformat="$,.0f",
        yaxis={"categoryorder": "array", "categoryarray": _category_array},
        legend_title="Make",
        margin=dict(l=0, r=20, t=10, b=40),
    )
    st.plotly_chart(fig1, use_container_width=True)

# ── Tab 2: Cost Breakdown ─────────────────────────────────────────────────────

with tab2:
    df_sorted_tco = df.sort_values("TCO")
    default_sel = df_sorted_tco["Label"].head(10).tolist()
    selected = st.multiselect(
        "Select vehicles to compare (sorted by TCO)",
        df_sorted_tco["Label"].tolist(),
        default=default_sel,
        key="breakdown_sel",
    )

    if not selected:
        st.info("Select vehicles above to see cost breakdown.")
    else:
        sub2 = df[df["Label"].isin(selected)].sort_values("TCO")

        component_map = {
            "Purchase": ("Purchase", "#4B5563"),
            "Fuel (PV)": ("PV_Fuel", "#F59E0B"),
            "Insurance (PV)": ("PV_Insurance", "#6366F1"),
            "Maintenance (PV)": ("PV_Maint", "#EF4444"),
            "Resale Credit": (None, "#059669"),
        }

        fig2 = go.Figure()
        for label, (col, color) in component_map.items():
            if col is not None:
                y_vals = sub2[col]
            else:
                y_vals = -sub2["PV_Resale"]
            fig2.add_trace(
                go.Bar(
                    name=label,
                    x=sub2["Label"],
                    y=y_vals,
                    marker_color=color,
                    hovertemplate=f"<b>{label}</b>: $%{{y:,.0f}}<extra></extra>",
                )
            )

        fig2.update_layout(
            barmode="relative",
            height=520,
            yaxis_title="Cost ($)",
            yaxis_tickformat="$,.0f",
            legend_title="Component",
            xaxis_tickangle=-30,
            margin=dict(b=130),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Resale Credit is negative — it reduces TCO. "
            "Net bar height = Total Cost of Ownership."
        )

# ── Tab 3: Scatter ────────────────────────────────────────────────────────────

with tab3:
    color_by = st.radio(
        "Color by", ["Powertrain", "Make"], horizontal=True, key="scatter_color"
    )

    df_scatter = df.copy()
    df_scatter["Cargo"] = df_scatter["Max_Cargo_cuft"].fillna(
        df_scatter["Max_Cargo_cuft"].median()
    )

    if color_by == "Powertrain":
        color_col = "Powertrain_Cat"
        color_map = PT_COLORS
        color_label = "Powertrain"
    else:
        color_col = "Make"
        color_map = MAKE_COLORS
        color_label = "Make"

    fig3 = px.scatter(
        df_scatter,
        x="Purchase",
        y="TCO",
        color=color_col,
        size="Cargo",
        size_max=18,
        hover_name="Label",
        hover_data={
            "Purchase": True,
            "TCO": True,
            "Powertrain": True,
            "Max_Cargo_cuft": True,
            color_col: False,
            "Cargo": False,
        },
        color_discrete_map=color_map,
        labels={
            "Purchase": "Purchase Price ($)",
            "TCO": "TCO ($)",
            "Powertrain_Cat": "Powertrain",
            "Max_Cargo_cuft": "Max Cargo (cu ft)",
        },
    )
    fig3.update_layout(
        height=600,
        xaxis_tickformat="$,.0f",
        yaxis_tickformat="$,.0f",
        legend_title=color_label,
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Bubble size = max cargo space (cu ft). Hover for details.")

# ── Tab 4: Sensitivity ────────────────────────────────────────────────────────

with tab4:
    st.subheader("TCO vs. Annual Miles")

    available_vehicles = df.sort_values("TCO")["Label"].tolist()
    sens_sel = st.multiselect(
        "Select up to 8 vehicles",
        available_vehicles,
        default=available_vehicles[:5],
        key="sens_sel",
    )
    if len(sens_sel) > 8:
        st.warning("Select 8 or fewer vehicles for a readable chart.")
        sens_sel = sens_sel[:8]

    total_mi = city_mi + hwy_mi
    city_frac = city_mi / max(total_mi, 1)

    miles_min, miles_max = st.slider(
        "Annual miles range",
        500,
        30_000,
        (500, 20_000),
        step=500,
        key="sens_miles",
    )

    if not sens_sel:
        st.info("Select vehicles above.")
    else:
        mile_points = np.arange(miles_min, miles_max + 500, 500)
        r_sens = discount_pct / 100.0
        g_sens = fuel_inflation_pct / 100.0
        pv_factor_sens = (
            (1 - (1 + r_sens) ** (-years)) / r_sens if r_sens > 0 else float(years)
        )
        if abs(r_sens - g_sens) > 1e-9:
            fuel_pv_factor_sens = (1 - ((1 + g_sens) / (1 + r_sens)) ** years) / (r_sens - g_sens)
        elif r_sens > 0:
            fuel_pv_factor_sens = years / (1 + r_sens)
        else:
            fuel_pv_factor_sens = float(years)

        fig4 = go.Figure()
        sub_sens = df[df["Label"].isin(sens_sel)]
        for _, row in sub_sens.iterrows():
            tcos = []
            for mi in mile_points:
                c = mi * city_frac
                h = mi * (1 - city_frac)
                annual_fuel = (
                    c * row["Fuel_cost_city_per_mile"] + h * row["Fuel_cost_hwy_per_mile"]
                )
                tco = (
                    row["Purchase"]
                    + annual_fuel * fuel_pv_factor_sens
                    + row["Annual_Insurance"] * pv_factor_sens
                    + row["Annual_Maint"] * pv_factor_sens
                    - row["PV_Resale"]
                )
                tcos.append(tco)

            fig4.add_trace(
                go.Scatter(
                    x=list(mile_points),
                    y=tcos,
                    name=row["Label"],
                    mode="lines",
                    hovertemplate="%{x:,} mi/yr → $%{y:,.0f}<extra>"
                    + row["Label"]
                    + "</extra>",
                )
            )

        if miles_min <= total_mi <= miles_max:
            fig4.add_vline(
                x=total_mi,
                line_dash="dash",
                line_color="rgba(100,100,100,0.6)",
                annotation_text=f"Current: {total_mi:,} mi/yr",
                annotation_position="top right",
            )

        fig4.update_layout(
            height=560,
            xaxis_title="Total Annual Miles",
            yaxis_title="TCO ($)",
            yaxis_tickformat="$,.0f",
            xaxis_tickformat=",",
            legend_title="Vehicle",
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(
            f"City/hwy split held at {city_frac:.0%}/{1-city_frac:.0%}. "
            "Resale held fixed at current ownership years."
        )

# ── Tab 5: Data Table ─────────────────────────────────────────────────────────

with tab5:
    display_cols = [
        "Label",
        "Year",
        "Make",
        "Model",
        "Trim",
        "Powertrain",
        "Purchase",
        "TCO",
        "Annual_Fuel",
        "Annual_Insurance",
        "Annual_Maint",
        "Resale_N",
        "IIHS_Rating",
        "RepairPal_5",
        "AWD_Standard",
        "AEB_Standard",
        "ACC_Standard",
        "Physical_HVAC_Controls",
        "Max_Cargo_cuft",
        "Cargo_2nd_Row_cuft",
    ]

    df_display = df[display_cols].sort_values("TCO").reset_index(drop=True)

    fmt_cols = ["Purchase", "TCO", "Annual_Fuel", "Annual_Insurance", "Annual_Maint", "Resale_N"]
    col_config = {
        "Label": st.column_config.TextColumn("Vehicle", width="large"),
    }
    for col in fmt_cols:
        col_config[col] = st.column_config.NumberColumn(
            col.replace("_", " ").replace("Annual ", "Annual "),
            format="$%.0f",
        )

    st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=col_config)

    csv_bytes = df_display.to_csv(index=False)
    st.download_button(
        "⬇️ Download filtered data as CSV",
        csv_bytes,
        "tco_comparison.csv",
        "text/csv",
    )

# ── Tab 6: My Listings ────────────────────────────────────────────────────────

with tab6:
    st.subheader("Add a Listing")

    if not FETCH_AVAILABLE:
        st.warning(
            "URL fetching requires extra packages. Run: `pip install requests beautifulsoup4`"
        )

    col_url, col_btn = st.columns([5, 1])
    url_input = col_url.text_input(
        "Paste listing URL",
        key="listing_url_input",
        placeholder="https://www.cars.com/... or https://www.kbb.com/...",
        label_visibility="collapsed",
    )
    fetch_clicked = col_btn.button("Fetch", use_container_width=True, key="fetch_btn")

    _PT_OPTIONS = ["Gas", "Hybrid", "PHEV"]

    if fetch_clicked and url_input:
        with st.spinner("Fetching listing..."):
            _fetched = fetch_listing(url_input)
        st.session_state["fetched_listing"] = _fetched
        # Seed form fields so they pre-fill with parsed values
        st.session_state["lst_year"] = int(_fetched.get("year") or 2021)
        st.session_state["lst_make"] = _fetched.get("make") or ""
        st.session_state["lst_model"] = _fetched.get("model") or ""
        st.session_state["lst_trim"] = _fetched.get("trim") or ""
        st.session_state["lst_price"] = int(_fetched.get("price") or 25000)
        st.session_state["lst_mileage"] = int(_fetched.get("mileage") or 25000)
        st.session_state["lst_powertrain"] = "Gas"
        st.session_state["lst_powertrain_seeded_for"] = None

    with st.expander("Paste page text instead (e.g. for KBB which blocks fetching)"):
        pasted_text = st.text_area(
            "Copy all text from the listing page (Ctrl+A, Ctrl+C) and paste here",
            height=160,
            key="listing_paste_text",
            label_visibility="collapsed",
            placeholder="2020 Toyota RAV4 XLE\n$27,998\n25,432 miles\n...",
        )
        parse_paste_clicked = st.button("Parse pasted text", key="parse_paste_btn")

    if parse_paste_clicked and pasted_text:
        _fetched = parse_pasted_text(pasted_text)
        st.session_state["fetched_listing"] = _fetched
        st.session_state["lst_year"] = int(_fetched.get("year") or 2021)
        st.session_state["lst_make"] = _fetched.get("make") or ""
        st.session_state["lst_model"] = _fetched.get("model") or ""
        st.session_state["lst_trim"] = _fetched.get("trim") or ""
        st.session_state["lst_price"] = int(_fetched.get("price") or 25000)
        st.session_state["lst_mileage"] = int(_fetched.get("mileage") or 25000)
        st.session_state["lst_powertrain"] = "Gas"
        st.session_state["lst_powertrain_seeded_for"] = None

    fetched = st.session_state.get("fetched_listing")

    if fetched is not None:
        conf = fetched.get("confidence", "failed")
        if conf == "parsed":
            st.success(f"Parsed via {fetched.get('source', 'unknown')} — review fields below")
        elif conf == "partial":
            st.warning(
                f"Partial data from {fetched.get('source', 'unknown')} — fill in missing fields"
            )
        else:
            err = fetched.get("raw_error", "")
            st.error(
                f"Could not parse automatically{f': {err}' if err else ''} — fill in fields manually"
            )

        st.divider()
        st.subheader("Review & Confirm")

        _c1, _c2, _c3 = st.columns(3)
        year_val = _c1.number_input(
            "Year", min_value=2010, max_value=2030, step=1, key="lst_year"
        )
        make_val = _c1.text_input("Make", key="lst_make")
        model_val = _c2.text_input("Model", key="lst_model")
        trim_val = _c2.text_input("Trim (optional)", key="lst_trim")
        price_val = _c3.number_input(
            "Listing Price ($)", min_value=1000, max_value=300000, step=100, key="lst_price"
        )
        mileage_val = _c3.number_input(
            "Mileage", min_value=0, max_value=500000, step=1000, key="lst_mileage"
        )
        label_val = _c3.text_input(
            "Custom label (optional)", key="lst_label",
            placeholder="e.g. 'RAV4 dealer A'"
        )

        match_result = match_to_csv(
            {"year": year_val, "make": make_val, "model": model_val,
             "trim": trim_val, "price": price_val},
            df_raw,
        )
        # Seed powertrain from CSV match only once per matched label (not on every render)
        _matched_pt = match_result["row"]["Powertrain"] if match_result["row"] is not None else None
        _match_label = match_result["row"]["Label"] if match_result["row"] is not None else None
        if _matched_pt and _matched_pt in _PT_OPTIONS and st.session_state.get("lst_powertrain_seeded_for") != _match_label:
            st.session_state["lst_powertrain"] = _matched_pt
            st.session_state["lst_powertrain_seeded_for"] = _match_label
        powertrain_val = _c1.selectbox(
            "Powertrain", _PT_OPTIONS,
            key="lst_powertrain",
        )
        _conf = match_result["confidence"]
        if _conf == "exact":
            st.success(f"Matched: {match_result['match_label']}")
        elif _conf in ("close", "model-only"):
            st.warning(f"Matched: {match_result['match_label']}")
        else:
            st.error(f"No CSV match — {match_result['match_label']}")

        matched_row = match_result["row"]
        if matched_row is not None:
            _csv_est = matched_row["Used_Price_Est_25K_mi"]
            if pd.notna(_csv_est):
                _delta = price_val - _csv_est
                _sign = "+" if _delta >= 0 else ""
                st.caption(
                    f"Listing price: **${price_val:,.0f}** · "
                    f"CSV estimate (~25K mi): **${_csv_est:,.0f}** · "
                    f"Delta: **{_sign}${_delta:,.0f}**"
                )

        _btn_col1, _btn_col2, _ = st.columns([1, 1, 4])
        save_clicked = _btn_col1.button("💾 Save", type="primary", key="save_listing_btn")
        cancel_clicked = _btn_col2.button("✕ Cancel", key="cancel_listing_btn")

        if save_clicked:
            _tco_snapshot = {}
            if matched_row is not None:
                _tco_row = compute_listing_tco(
                    matched_row, float(price_val),
                    years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct,
                    listing_mileage=float(mileage_val),
                )
                _tco_snapshot = {
                    k: float(_tco_row[k])
                    for k in ["TCO", "Purchase", "PV_Fuel", "PV_Insurance", "PV_Maint",
                              "PV_Resale", "Resale_N"]
                    if k in _tco_row.index
                }
            _entry = {
                "url": url_input,
                "label": (label_val.strip()
                          or f"{year_val} {make_val} {model_val} {trim_val} {powertrain_val}".strip()),
                "year": int(year_val),
                "make": make_val,
                "model": model_val,
                "trim": trim_val,
                "powertrain": powertrain_val,
                "listing_price": float(price_val),
                "mileage": int(mileage_val),
                "matched_csv_key": matched_row["Label"] if matched_row is not None else None,
                "match_confidence": _conf,
                "tco_snapshot": _tco_snapshot,
                "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            _existing = load_listings()
            _existing.append(_entry)
            save_listings(_existing)
            del st.session_state["fetched_listing"]
            st.rerun()

        if cancel_clicked:
            del st.session_state["fetched_listing"]
            st.rerun()

    # ── Saved listings table ──────────────────────────────────────────────────
    st.divider()
    st.subheader("Saved Listings")
    all_listings = load_listings()

    if not all_listings:
        st.info("No listings saved yet. Paste a URL above to get started.")
    else:
        _fleet_min_tco = df["TCO"].min() if not df.empty else None

        _rows = []
        for _i, _lst in enumerate(all_listings):
            _csv_key = _lst.get("matched_csv_key")
            _tco_val = None
            _csv_est = None
            if _csv_key:
                _m = df_raw[df_raw["Label"] == _csv_key]
                if not _m.empty:
                    _tco_row = compute_listing_tco(
                        _m.iloc[0], _lst["listing_price"],
                        years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct,
                        listing_mileage=_lst.get("mileage", 25000),
                    )
                    _tco_val = float(_tco_row["TCO"])
                    _csv_est = float(_m.iloc[0]["Used_Price_Est_25K_mi"])
            _rows.append({
                "_idx": _i,
                "Vehicle": _lst["label"],
                "Mileage": _lst.get("mileage"),
                "Listing Price": _lst["listing_price"],
                "CSV Est (~25K mi)": _csv_est,
                "Delta": (_lst["listing_price"] - _csv_est) if _csv_est is not None else None,
                "TCO": _tco_val,
                "vs Fleet Best": ((_tco_val - _fleet_min_tco) if (_tco_val and _fleet_min_tco) else None),
                "Match": _lst.get("match_confidence", ""),
                "URL": _lst.get("url", ""),
            })

        _disp_df = pd.DataFrame(_rows).sort_values("TCO", ascending=True, na_position="last")
        _money_cols = ["Listing Price", "CSV Est (~25K mi)", "Delta", "TCO", "vs Fleet Best"]
        _col_cfg = {
            "Vehicle": st.column_config.TextColumn("Vehicle", width="large"),
            "Mileage": st.column_config.NumberColumn("Mileage", format="%d mi"),
            "URL": st.column_config.LinkColumn("Link"),
        }
        for _col in _money_cols:
            _col_cfg[_col] = st.column_config.NumberColumn(_col, format="$%.0f")

        st.dataframe(
            _disp_df.drop(columns=["_idx"]),
            use_container_width=True,
            hide_index=True,
            column_config=_col_cfg,
        )

        for _i, _lst in enumerate(all_listings):
            _rc_name, _rc_edit, _rc_del = st.columns([6, 1, 1])
            _rc_name.write(_lst["label"])
            if _rc_edit.button("✏️ Edit", key=f"edit_listing_{_i}"):
                st.session_state["editing_listing_idx"] = _i
                st.rerun()
            if _rc_del.button("✕ Delete", key=f"del_listing_{_i}"):
                save_listings([l for j, l in enumerate(all_listings) if j != _i])
                if st.session_state.get("editing_listing_idx") == _i:
                    del st.session_state["editing_listing_idx"]
                st.rerun()

        # ── Inline edit form ──────────────────────────────────────────────────
        _edit_idx = st.session_state.get("editing_listing_idx")
        if _edit_idx is not None and _edit_idx < len(all_listings):
            _e = all_listings[_edit_idx]
            st.divider()
            st.subheader(f"Edit: {_e['label']}")
            _e1, _e2, _e3 = st.columns(3)
            _e_label = _e1.text_input("Label", value=_e.get("label", ""), key="edit_label")
            _e_price = _e2.number_input(
                "Listing Price ($)", min_value=1000, max_value=300000, step=100,
                value=int(_e.get("listing_price", 25000)), key="edit_price",
            )
            _e_mileage = _e3.number_input(
                "Mileage", min_value=0, max_value=500000, step=1000,
                value=int(_e.get("mileage", 25000)), key="edit_mileage",
            )

            # CSV match selector — changing this updates powertrain + TCO costs
            _all_csv_labels = ["(none)"] + df_raw["Label"].tolist()
            _current_match = _e.get("matched_csv_key") or "(none)"

            def _on_match_change():
                sel = st.session_state["edit_csv_match"]
                if sel and sel != "(none)":
                    _match_row = df_raw[df_raw["Label"] == sel]
                    _pt = _match_row.iloc[0]["Powertrain"] if not _match_row.empty else ""
                    st.session_state["edit_label"] = f"{sel} {_pt}".strip() if _pt else sel

            _e_match = st.selectbox(
                "CSV match (determines powertrain & operating costs)",
                _all_csv_labels,
                index=_all_csv_labels.index(_current_match) if _current_match in _all_csv_labels else 0,
                key="edit_csv_match",
                on_change=_on_match_change,
            )

            _upd1, _upd2, _ = st.columns([1, 1, 4])
            if _upd1.button("💾 Update", type="primary", key="update_listing_btn"):
                _new_match_key = _e_match if _e_match != "(none)" else None
                _new_match_row = df_raw[df_raw["Label"] == _new_match_key].iloc[0] if _new_match_key else None
                _tco_snap = {}
                if _new_match_row is not None:
                    _tr = compute_listing_tco(
                        _new_match_row, float(_e_price),
                        years, city_mi, hwy_mi, discount_pct, fuel_inflation_pct,
                        listing_mileage=float(_e_mileage),
                    )
                    _tco_snap = {
                        k: float(_tr[k]) for k in
                        ["TCO", "Purchase", "PV_Fuel", "PV_Insurance", "PV_Maint", "PV_Resale", "Resale_N"]
                        if k in _tr.index
                    }
                all_listings[_edit_idx] = {
                    **_e,
                    "label": _e_label.strip() or _e["label"],
                    "listing_price": float(_e_price),
                    "mileage": int(_e_mileage),
                    "matched_csv_key": _new_match_key,
                    "powertrain": _new_match_row["Powertrain"] if _new_match_row is not None else _e.get("powertrain", ""),
                    **_tco_snap,
                }
                save_listings(all_listings)
                del st.session_state["editing_listing_idx"]
                st.rerun()
            if _upd2.button("Cancel", key="cancel_edit_btn"):
                del st.session_state["editing_listing_idx"]
                st.rerun()

        if st.button("🗑️ Clear All Listings", key="clear_all_listings"):
            save_listings([])
            st.rerun()
