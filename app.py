import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

VT_URL = "https://www.nerunner.com/states/vermont/"
NH_URL = "https://www.nerunner.com/states/new-hampshire/"
ALLOWED_MONTHS = {"may", "jun", "jul", "aug", "sep", "oct"}

@st.cache_data(ttl=3600)
def scrape_state(url: str, state_name: str):
    headers = {"User-Agent": "NERunner-10K-Scraper/1.0"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")
    lines = [
        re.sub(r"\s+", " ", ln).strip()
        for ln in text.split("\n")
        if ln.strip()
    ]

    listing_start = re.compile(r"^(\d{1,2})\s+([a-z]{3})\s+", re.IGNORECASE)
    races = []

    for ln in lines:
        m = listing_start.match(ln)
        if not m:
            continue

        day = m.group(1).zfill(2)
        mon = m.group(2).lower()

        if mon not in ALLOWED_MONTHS:
            continue

        if "Race Distance:" not in ln:
            continue
        if "10K" not in ln:
            continue

        races.append(
            {
                "Date": f"{mon.upper()} {day}",
                "State": state_name,
                "Listing": ln,
            }
        )

    return races

st.set_page_config(page_title="VT + NH 10K Races (May–Oct)", layout="wide")
st.title("VT + NH 10K Races (May–Oct)")

choice = st.selectbox("State", ["Both", "Vermont", "New Hampshire"])

if st.button("Force refresh (re-scrape)"):
    st.cache_data.clear()

rows = []
with st.spinner("Scraping NERunner…"):
    if choice in ("Both", "Vermont"):
        rows += scrape_state(VT_URL, "Vermont")
    if choice in ("Both", "New Hampshire"):
        rows += scrape_state(NH_URL, "New Hampshire")

st.caption(f"{len(rows)} races found (cached for 1 hour).")
st.dataframe(rows, use_container_width=True, hide_index=True)
