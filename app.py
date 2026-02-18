import re
import streamlit as st
import requests
from bs4 import BeautifulSoup

CAL_URL = "https://www.nerunner.com/race-calendar/"

ALLOWED_MONTHS = ["may", "jun", "jul", "aug", "sep", "oct"]
ALLOWED_STATES = {"vermont": "Vermont", "new hampshire": "New Hampshire"}

@st.cache_data(ttl=3600)
def fetch_lines(url: str):
    headers = {"User-Agent": "NERunner-10K-Scraper/1.0"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]
    return lines

def parse_calendar(lines):
    """
    Looks for event lines that contain:
      - a date like "03 may"
      - "Race Distance:" and includes "10K"
      - "State:" includes Vermont and/or New Hampshire
    """
    events = []
    date_re = re.compile(r"^(\d{1,2})\s+(%s)\b" % "|".join(ALLOWED_MONTHS), re.IGNORECASE)

    for ln in lines:
        m = date_re.match(ln)
        if not m:
            continue

        day = m.group(1).zfill(2)
        mon = m.group(2).lower()

        if "Race Distance:" not in ln or "State:" not in ln:
            continue
        if "10K" not in ln.upper():
            continue

        # Extract state(s)
        st_match = re.search(r"State:\s*([^ ](?:.*))$", ln)
        # More robust: stop at end, but if other labels exist after State it can get messy.
        # We'll just capture after "State:" and then split by spaces/commas heuristically.
        state_blob = ln.split("State:", 1)[1].strip()
        # often "Vermont" or "Maine,New Hampshire" etc.
        state_candidates = [s.strip() for s in re.split(r"[,\|/]", state_blob) if s.strip()]

        matched_states = []
        for s in state_candidates:
            key = s.lower()
            if key in ALLOWED_STATES:
                matched_states.append(ALLOWED_STATES[key])

        if not matched_states:
            # Sometimes blob includes extra words; try substring match
            blob_l = state_blob.lower()
            if "vermont" in blob_l:
                matched_states.append("Vermont")
            if "new hampshire" in blob_l:
                matched_states.append("New Hampshire")

        if not matched_states:
            continue

        # Extract distance list
        dist_blob = ln.split("Race Distance:", 1)[1]
        dist_blob = dist_blob.split("State:", 1)[0].strip()
        distances = [d.strip() for d in dist_blob.split(",") if d.strip()]

        # Ensure it's truly a 10K option (not just “10K/5K” text weirdness)
        if not any(d.upper() == "10K" for d in distances) and "10K" not in dist_blob.upper():
            continue

        # Try to pull a nicer race name: between first time and next time (common on this site)
        time_matches = list(re.finditer(r"(\d{1,2}:\d{2}\s*(?:am|pm))", ln, re.IGNORECASE))
        race_name = ln
        start_time = ""
        if time_matches:
            start_time = time_matches[0].group(1).lower()
            if len(time_matches) >= 2:
                race_name = ln[time_matches[0].end():time_matches[1].start()].strip(" -–—")
            else:
                # up to Race Director if present
                after = ln[time_matches[0].end():]
                race_name = re.split(r"\s+Race Director:\s+", after, maxsplit=1)[0].strip(" -–—")

        for st_name in matched_states:
            events.append({
                "Date": f"{mon.upper()} {day}" + (f" • {start_time}" if start_time else ""),
                "State": st_name,
                "Race": race_name,
                "Distances": ", ".join(distances) if distances else "10K",
                "Source line": ln,
            })

    # De-dupe
    seen = set()
    out = []
    for e in events:
        k = (e["Date"], e["State"], e["Race"])
        if k not in seen:
            seen.add(k)
            out.append(e)

    return out

st.set_page_config(page_title="VT + NH 10K Races (May–Oct)", layout="wide")
st.title("VT + NH 10K Races (May–Oct)")

choice = st.selectbox("State", ["Both", "Vermont", "New Hampshire"])
debug = st.checkbox("Debug", value=False)

if st.button("Force refresh (re-scrape)"):
    st.cache_data.clear()

with st.spinner("Scraping NERunner race calendar…"):
    lines = fetch_lines(CAL_URL)
    events = parse_calendar(lines)

if choice != "Both":
    events = [e for e in events if e["State"] == choice]

st.caption(f"{len(events)} races found (cached for 1 hour).")
st.dataframe(events, use_container_width=True, hide_index=True)

if debug:
    st.write({
        "calendar_lines": len(lines),
        "sample_lines_with_10k": [ln for ln in lines if "10K" in ln.upper()][:20],
    })
