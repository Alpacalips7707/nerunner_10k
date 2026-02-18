import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

VT_URL = "https://www.nerunner.com/states/vermont/"
NH_URL = "https://www.nerunner.com/states/new-hampshire/"

# Accept both 3-letter and full month names (because the site text can vary)
MONTHS = [
    ("may", ["may"]),
    ("jun", ["jun", "june"]),
    ("jul", ["jul", "july"]),
    ("aug", ["aug", "august"]),
    ("sep", ["sep", "sept", "september"]),
    ("oct", ["oct", "october"]),
]
MONTH_WORDS = {w for _, words in MONTHS for w in words}

DATE_PATTERNS = [
    # "03 may" or "3 may"
    re.compile(r"^\s*(\d{1,2})\s+(may|jun|jul|aug|sep|oct)\b", re.IGNORECASE),
    # "may 03" or "may 3"
    re.compile(r"^\s*(may|june|july|august|sept|september|oct|october)\s+(\d{1,2})\b", re.IGNORECASE),
]

def normalize_month(token: str) -> str:
    t = token.lower()
    for short, words in MONTHS:
        if t in words or t == short:
            return short
    return t[:3]

@st.cache_data(ttl=3600)
def fetch_lines(url: str):
    headers = {"User-Agent": "NERunner-10K-Scraper/1.0"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]
    return lines

def find_nearest_date(lines, idx):
    # Walk up a bit to find a nearby date line
    for j in range(max(0, idx - 30), idx)[::-1]:
        ln = lines[j]
        for pat in DATE_PATTERNS:
            m = pat.match(ln)
            if m:
                # pattern 1: day, mon   pattern 2: mon, day
                if pat is DATE_PATTERNS[0]:
                    day = m.group(1)
                    mon = normalize_month(m.group(2))
                else:
                    mon = normalize_month(m.group(1))
                    day = m.group(2)
                return mon.upper(), str(day).zfill(2)
    return None, None

def month_in_window(text: str) -> bool:
    t = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in MONTH_WORDS)

def extract_race_name(lines, idx):
    """
    Heuristic: race name is often near the distance line.
    We'll look a few lines above for something "title-like".
    """
    for j in range(max(0, idx - 6), idx)[::-1]:
        ln = lines[j]
        # Skip obvious labels
        if "race distance" in ln.lower() or "race type" in ln.lower() or "race director" in ln.lower():
            continue
        # Prefer lines that look like a title (not too long)
        if 4 <= len(ln) <= 120:
            return ln
    return lines[idx]

def build_rows(state_name: str, url: str):
    lines = fetch_lines(url)

    rows = []

    for i, ln in enumerate(lines):
        low = ln.lower()

        # Primary signal: distance label + 10K
        if "race distance" in low and "10k" in low:
            mon, day = find_nearest_date(lines, i)
            # If we couldn't find a date nearby, keep it but mark unknown
            date_str = f"{mon} {day}" if mon and day else "DATE ?"

            # Month filter: use date if found; otherwise allow if any month word appears nearby
            if mon:
                if mon.lower() not in {"MAY","JUN","JUL","AUG","SEP","OCT"}:
                    continue
            else:
                # fallback month filter by nearby context
                context = " ".join(lines[max(0, i-20): i+1]).lower()
                if not month_in_window(context):
                    continue

            name = extract_race_name(lines, i)

            rows.append({
                "Date": date_str,
                "State": state_name,
                "Race": name,
                "Distance line": ln,
            })

    # De-duplicate (sometimes the distance line appears twice)
    seen = set()
    deduped = []
    for r in rows:
        key = (r["Date"], r["State"], r["Race"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped, lines

st.set_page_config(page_title="VT + NH 10K Races (May–Oct)", layout="wide")
st.title("VT + NH 10K Races (May–Oct)")

choice = st.selectbox("State", ["Both", "Vermont", "New Hampshire"])
debug = st.checkbox("Debug (show sample matches)", value=False)

if st.button("Force refresh (re-scrape)"):
    st.cache_data.clear()

rows = []
debug_info = {}

with st.spinner("Scraping NERunner…"):
    if choice in ("Both", "Vermont"):
        vt_rows, vt_lines = build_rows("Vermont", VT_URL)
        rows += vt_rows
        debug_info["VT_total_lines"] = len(vt_lines)
        debug_info["VT_rows"] = len(vt_rows)
    if choice in ("Both", "New Hampshire"):
        nh_rows, nh_lines = build_rows("New Hampshire", NH_URL)
        rows += nh_rows
        debug_info["NH_total_lines"] = len(nh_lines)
        debug_info["NH_rows"] = len(nh_rows)

st.caption(f"{len(rows)} races found (cached for 1 hour).")
st.dataframe(rows, use_container_width=True, hide_index=True)

if debug:
    st.subheader("Debug")
    st.write(debug_info)
