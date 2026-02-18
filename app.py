import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

VT_URL = "https://www.nerunner.com/states/vermont/"
NH_URL = "https://www.nerunner.com/states/new-hampshire/"
ALLOWED_MONTHS = {"may", "jun", "jul", "aug", "sep", "oct"}

@st.cache_data(ttl=3600)
def scrape_state(url, state_name):
    headers = {"User-Agent": "NERunner-10K-Scraper"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]

    races = []
    listing_start = re.compile(r"^(\d{1,2})\s+([a-z]{3})", re.IGNORECASE)

    for ln in lines:
        m = listing_start.match(ln)
        if not m:
            continue

        day = m.group(1).zfill(2)
        mon = m.group(2).lower()

        if mon not in ALLOWED_MONTHS:
            continue

        if "Race
