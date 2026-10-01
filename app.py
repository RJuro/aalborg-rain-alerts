import os
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from backend import DEFAULT_BASE_URL, BackendError, fetch_weather, subscribe

st.set_page_config(page_title="Aalborg Rain · A little heads-up", page_icon="☂", layout="wide")
AALBORG = ZoneInfo("Europe/Copenhagen")

def setting(key, default):
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(key, default)

BASE_URL = setting("N8N_BASE_URL", DEFAULT_BASE_URL)
SIGNUPS_ENABLED = str(setting("SUBSCRIPTIONS_ENABLED", False)).lower() in ("true", "1", "yes")

@st.cache_data(ttl=300, show_spinner=False)
def get_forecast(base_url):
    return fetch_weather(base_url)

def local_time(value, pattern="%H:%M"):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(AALBORG).strftime(pattern)

st.html("""
<style>
.stMainBlockContainer{max-width:1180px;padding-top:2.4rem;padding-bottom:2rem}
h1,h2,h3{color:#183444}
header[data-testid="stHeader"]{background:transparent}
.brand{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #cfcfc4;padding-bottom:20px;margin-bottom:34px;color:#294452;font-size:12px;letter-spacing:.17em;font-weight:650}
.brand .place{font-weight:400;letter-spacing:.06em}
.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:650;color:#547078;text-transform:uppercase}
.hero h1{font:clamp(42px,5vw,68px)/1.05 Georgia,serif;letter-spacing:-.035em;margin:14px 0 22px;max-width:680px}
.hero p{font-size:18px;line-height:1.6;color:#52646d;max-width:600px}
.status{display:inline-flex;align-items:center;gap:9px;font-size:12px;color:#24565c;background:#e6ede5;border:1px solid #cbdaca;border-radius:99px;padding:7px 12px;margin-bottom:12px}
.status.wet{background:#dfeaf2;border-color:#b9d1df;color:#205975}
.dot{height:7px;width:7px;border-radius:50%;background:currentColor}
.big-number{font:64px/1 Georgia,serif;color:#205975;margin-top:10px}
.number-label{font-size:12px;line-height:1.5;color:#62717a;margin:10px 0 24px}
.small-metric{border-top:1px solid #d6d5cc;padding:14px 0 22px}
.small-metric strong{font:24px Georgia,serif;display:block;margin-bottom:6px}
.small-metric span{font-size:12px;color:#65747b}
.forecast-title{font:28px Georgia,serif;margin:30px 0 4px}
[data-testid="stForm"]{background:#eeeae1;border:1px solid #d9d6cc;padding:24px;border-radius:14px}
[data-testid="stForm"] h3{font:29px/1.15 Georgia,serif}
[data-testid="stForm"] p{color:#5d6b70;line-height:1.5}
[data-testid="stBaseButton-primary"]{background:#205975;border-color:#205975;border-radius:8px;min-height:46px}
footer{visibility:hidden}
.footer{border-top:1px solid #d6d5cc;margin-top:36px;padding-top:16px;font-size:11px;line-height:1.8;color:#6b777b;display:flex;justify-content:space-between;gap:20px}
.footer a{color:#526976}
@media(max-width:640px){.stMainBlockContainer{padding-top:1.3rem}.brand{margin-bottom:24px}.brand .place{display:none}.hero h1{font-size:43px}.footer{display:block}}
</style>
<div class="brand"><span>☂ &nbsp; AALBORG RAIN</span><span class="place">57.048° N &nbsp; 9.919° E · DENMARK</span></div>
""")

left, right = st.columns([2.05, 1], gap="large")
forecast = None
with left:
    try:
        with st.spinner("Checking the skies over Aalborg…"):
            forecast = get_forecast(BASE_URL)
    except BackendError as exc:
        st.html('<div class="hero"><div class="eyebrow">A LITTLE HEADS-UP</div><h1>The forecast is taking a rain check.</h1></div>')
        st.warning(str(exc))

    if forecast:
        wet = forecast["rain_likely"]
        horizon = int(forecast["horizon_hours"])
        status = "Rain looks likely" if wet else "Below the alert threshold"
        headline = "An umbrella kind<br>of day." if wet else "One less thing<br>to check."
        subheading = (
            f'Rain could arrive around {local_time(forecast["first_rain_start"])}. A little warning before you head out.'
            if wet else f'The next {horizon} hours are below our rain alert threshold. Keep an eye on the hourly outlook below.'
        )
        st.html(f'<div class="hero"><div class="status {"wet" if wet else ""}"><span class="dot"></span>{status}</div><div class="eyebrow">A LITTLE HEADS-UP</div><h1>{headline}</h1><p>{escape(subheading)}</p></div>')
        chance, temperature, rain = st.columns(3)
        with chance:
            st.html(f'<div class="big-number">{forecast["max_hourly_probability"]:.0f}%</div><div class="number-label">Highest hourly precipitation chance<br>in the next {horizon} hours</div>')
        with temperature:
            temp = forecast.get("current_temperature_c")
            value = f"{temp:.0f}°" if isinstance(temp, (int, float)) else "—"
            st.html(f'<div class="big-number">{value}</div><div class="number-label">Temperature<br>in Aalborg now</div>')
        with rain:
            st.html(f'<div class="big-number">{forecast["expected_rain_mm"]:.1f}</div><div class="number-label">Forecast rain + showers, mm<br>across the upcoming hourly intervals</div>')

        st.html('<div class="forecast-title">The hours ahead</div>')
        st.caption("Hourly precipitation chance · times in Aalborg")
        hourly = pd.DataFrame(forecast["hours"][:12])
        hourly["Time"] = hourly["start"].map(local_time)
        hourly["Chance"] = hourly["probability"]
        hourly["Rain (mm)"] = hourly["rain_mm"]
        hourly["Qualifies"] = ((hourly["Chance"] >= forecast["threshold_percent"]) & (hourly["Rain (mm)"] >= forecast["minimum_rain_mm"])).map({True: "Meets alert rule", False: "Below alert rule"})
        bars = alt.Chart(hourly).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Time:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelPadding=8)),
            y=alt.Y("Chance:Q", title=None, scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(values=[0, 30, 60, 100], labelExpr="datum.value + '%'")),
            color=alt.Color("Qualifies:N", scale=alt.Scale(domain=["Meets alert rule", "Below alert rule"], range=["#205975", "#afc4ca"]), legend=None),
            tooltip=["Time:N", alt.Tooltip("Chance:Q", title="Chance (%)"), "Rain (mm):Q", "Qualifies:N"],
        )
        rule = alt.Chart(pd.DataFrame({"threshold": [forecast["threshold_percent"]]})).mark_rule(strokeDash=[4, 4], color="#7c8e93").encode(y="threshold:Q")
        st.altair_chart((bars + rule).properties(height=210).configure_view(stroke=None).configure_axis(gridColor="#dedfd8", labelColor="#65747b").configure(background="#F6F3EC"), width="stretch")
        st.caption(f'Dashed line: {int(forecast["threshold_percent"])}% threshold. Dark bars also meet the {forecast["minimum_rain_mm"]} mm rain rule. The percentage is per hour, not the chance of rain over the entire six-hour window.')
        st.caption(f'Last checked {local_time(forecast["fetched_at"])} · cached for up to five minutes. Refresh to check again.')
        if st.button("Refresh forecast", type="tertiary"):
            get_forecast.clear()
            st.rerun()

with right:
    with st.form("rain_subscription", clear_on_submit=False):
        st.markdown("### Let the forecast come to you.")
        st.write("Get an email when rain looks likely in Aalborg. Handy before the commute, a walk, or a trip into town.")
        email = st.text_input("Your email", placeholder="you@example.com", max_chars=254)
        consent = st.checkbox("I agree to receive Aalborg rain alerts by email.")
        submitted = st.form_submit_button("Send me rain alerts  →", type="primary", width="stretch", disabled=not SIGNUPS_ENABLED)
        st.caption("Confirm your email to start. Unsubscribe whenever you like.")
        if not SIGNUPS_ENABLED:
            st.caption("Email subscriptions are opening soon.")
    if submitted and SIGNUPS_ENABLED:
        try:
            with st.spinner("Sending your confirmation link…"):
                receipt = subscribe(email, consent, BASE_URL)
            st.success(receipt)
        except BackendError as exc:
            st.error(str(exc))
    threshold = int(forecast["threshold_percent"]) if forecast else 60
    horizon = int(forecast["horizon_hours"]) if forecast else 6
    minimum = forecast["minimum_rain_mm"] if forecast else 0.2
    cooldown = int(forecast["cooldown_hours"]) if forecast else 6
    st.markdown("#### A useful warning. A quieter inbox.")
    st.write(f"We check once an hour. An alert needs at least a {threshold}% precipitation chance and {minimum} mm of predicted rain or showers in an hour within the next {horizon} hours.")
    st.caption(f"At least {cooldown} hours between emails. Forecasts can change.")
    with st.expander("What we store"):
        st.write("Your email, confirmation and unsubscribe tokens, subscription status, and the last alert time. Your address stays in the subscription table and is used to send these emails.")

st.html('<div class="footer"><span>AALBORG RAIN · A little heads-up for your everyday.</span><span>Weather data from <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> · Forecasts, not guarantees.</span></div>')
