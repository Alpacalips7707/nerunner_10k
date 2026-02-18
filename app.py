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
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]

    listing_start = re.compile(r"^(\d{1,2})\s+([a-z]{3})\s+", re.IGNORECASE)
    races = []

    for ln in lines:
