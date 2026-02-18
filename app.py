import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

BASE = "https://www.runningintheusa.com"
STATE_CODES = {"Vermont": "vt", "New Hampshire": "nh"}
MONTHS = ["may", "jun", "jul", "aug", "sep", "oct"]

@st.cache_data(ttl=3600)
def fetch_page(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Streamlit; personal use)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def extract_races(html: str, state_name: str, month: str):
    soup = BeautifulSoup(html, "html.parser")

    # Race pages have lots of repeated text; simplest reliable approach:
    # grab links that look like race detail pages and use their nearby text.
    links = soup.find_all("a", href=True)
    races = []

    for a in links:
        href = a["href"]
        text = " ".join(a.get_text(" ", strip=True).split())
        if not text:
            continue

        # Race detail links usually contain "/race/" and have a race name in the anchor text
        if "/race/" not in href:
            continue

        # Pull a chunk of surrounding text (parent container) to find date + distance
        container = a.parent
        chunk = container.get_text(" ", strip=True) if container else text
        chunk = " ".join(chunk.split())

        # Must include 10K somewhere in the chunk
        if "10K" not in chunk.upper():
            continue

        # Try to find a date like "May 3, 2026" in the chunk
        date_match = re.search(rf"\b{month}\b\s+\d{{1,2}},\s+\d{{4}}", chunk, re.IGNORECASE)
        date_str = date_match.group(0).title() if date_match else month.upper()

        # Make absolute URL
        if href.startswith("/"):
            url = BASE + href
        elif href.startswith("http"):
            url = href
        else:
            url = BASE + "/" + href.lstrip("/")

        races.append(
            {
                "Date": date_str,
                "State": state_name,
                "Race": text,
                "Link": url,
            }
        )

    # De-dupe
    seen = set()
    out = []
    for r in races:
        k = (r["Date"], r["State"], r["Race"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out

st.set_page_config(page_title="VT + NH 10K Races (May–Oct)", layout="wide")
st.title("VT + NH 10K Races (May–Oct)")

state_choice = st.selectbox("State", ["Both", "Vermont", "New Hampshire"])
debug = st.checkbox("Debug", value=False)

if st.button("Force refresh (re-scrape)"):
    st.cache_data.clear()

rows = []
with st.spinner("Scraping runningintheusa.com…"):
    for state_name, code in STATE_CODES.items():
        if state_choice != "Both" and state_choice != state_name:
            continue

        for m in MONTHS:
            url = f"{BASE}/race/list/{code}/{m}/sort-by-open-date"
            html = fetch_page(url)
            rows += extract_races(html, state_name, m)

st.caption(f"{len(rows)} races found (cached for 1 hour).")
st.dataframe(rows, use_container_width=True, hide_index=True)

if debug:
    st.write({
        "example_source_pages": {
            "VT May": f"{BASE}/race/list/vt/may/sort-by-open-date",
            "NH May": f"{BASE}/race/list/nh/may/sort-by-open-date",
        }
    })
