from __future__ import annotations

import base64
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from html import escape
from html.parser import HTMLParser
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path

import joblib
import pandas as pd
import pydeck as pdk
import streamlit as st
from streamlit.delta_generator import DeltaGenerator


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
FLY_DIR = PROJECT_ROOT / "fly"
MODEL_DIR = Path(os.getenv("MODEL_DIR", FLY_DIR / "flight_delay_model_artifacts")).expanduser()
MODEL_PATH = Path(os.getenv("MODEL_PATH", MODEL_DIR / "best_delay_model_pipeline.joblib")).expanduser()
METADATA_PATH = Path(os.getenv("METADATA_PATH", MODEL_DIR / "best_delay_model_metadata.json")).expanduser()
THRESHOLDS_PATH = Path(os.getenv("THRESHOLDS_PATH", MODEL_DIR / "best_model_thresholds.csv")).expanduser()
AIRPORTS_PATH = Path(os.getenv("AIRPORTS_PATH", PROJECT_ROOT / "airports.csv")).expanduser()
HEADER_IMAGE_PATH = APP_DIR / "assets" / "flight-assistant-header.png"

if str(FLY_DIR) not in sys.path:
    sys.path.insert(0, str(FLY_DIR))


POPULAR_AIRPORTS = [
    "ATL",
    "AUS",
    "BNA",
    "BOS",
    "BWI",
    "CHS",
    "CLE",
    "CLT",
    "CMH",
    "CVG",
    "DCA",
    "DEN",
    "DFW",
    "DTW",
    "EWR",
    "FLL",
    "HNL",
    "HOU",
    "IAD",
    "IAH",
    "IND",
    "JFK",
    "LAS",
    "LAX",
    "LGA",
    "MCI",
    "MCO",
    "MDW",
    "MEM",
    "MIA",
    "MKE",
    "MSP",
    "MSY",
    "OAK",
    "ONT",
    "ORD",
    "PBI",
    "PDX",
    "PHL",
    "PHX",
    "PIT",
    "RDU",
    "RSW",
    "SAN",
    "SAT",
    "SDF",
    "SEA",
    "SFO",
    "SJC",
    "SJU",
    "SLC",
    "SMF",
    "SNA",
    "STL",
    "TPA",
    "TUS",
    "YVR",
    "YYC",
    "YUL",
    "YYZ",
    "MEX",
    "CUN",
    "GDL",
    "BOG",
    "LIM",
    "GRU",
    "GIG",
    "SCL",
    "EZE",
    "PTY",
    "SJO",
    "LHR",
    "LGW",
    "CDG",
    "ORY",
    "AMS",
    "FRA",
    "MUC",
    "ZRH",
    "MAD",
    "BCN",
    "FCO",
    "MXP",
    "DUB",
    "IST",
    "CPH",
    "OSL",
    "ARN",
    "HEL",
    "DOH",
    "DXB",
    "AUH",
    "JED",
    "RUH",
    "DEL",
    "BOM",
    "BLR",
    "SIN",
    "KUL",
    "BKK",
    "HKG",
    "TPE",
    "ICN",
    "GMP",
    "NRT",
    "HND",
    "KIX",
    "PVG",
    "PEK",
    "CAN",
    "MNL",
    "CGK",
    "SYD",
    "MEL",
    "BNE",
    "AKL",
    "JNB",
    "CPT",
    "CAI",
    "ADD",
    "NBO",
]

AIRLINES = {
    "Aer Lingus": "EI",
    "Aeromexico": "AM",
    "Air Canada": "AC",
    "Air China": "CA",
    "Air France": "AF",
    "Air India": "AI",
    "Air New Zealand": "NZ",
    "AirAsia": "AK",
    "American Airlines": "AA",
    "Alaska Airlines": "AS",
    "All Nippon Airways": "NH",
    "Allegiant Air": "G4",
    "Austrian Airlines": "OS",
    "Avianca": "AV",
    "British Airways": "BA",
    "Cathay Pacific": "CX",
    "Cebu Pacific": "5J",
    "China Airlines": "CI",
    "China Eastern": "MU",
    "China Southern": "CZ",
    "CommutAir": "C5",
    "Copa Airlines": "CM",
    "JetBlue": "B6",
    "Delta Air Lines": "DL",
    "EasyJet": "U2",
    "Egyptair": "MS",
    "Emirates": "EK",
    "Endeavor Air": "9E",
    "Envoy Air": "MQ",
    "Etihad Airways": "EY",
    "Ethiopian Airlines": "ET",
    "EVA Air": "BR",
    "Finnair": "AY",
    "Frontier Airlines": "F9",
    "Garuda Indonesia": "GA",
    "GoJet Airlines": "G7",
    "Hawaiian Airlines": "HA",
    "Horizon Air": "QX",
    "Iberia": "IB",
    "ITA Airways": "AZ",
    "Japan Airlines": "JL",
    "Kenya Airways": "KQ",
    "KLM Royal Dutch Airlines": "KL",
    "Korean Air": "KE",
    "LATAM Airlines": "LA",
    "Lufthansa": "LH",
    "Malaysia Airlines": "MH",
    "Mesa Airlines": "YV",
    "Pegasus Airlines": "PC",
    "Philippine Airlines": "PR",
    "Piedmont Airlines": "PT",
    "PSA Airlines": "OH",
    "Qantas": "QF",
    "Qatar Airways": "QR",
    "Republic Airways": "YX",
    "Ryanair": "FR",
    "S7 Airlines": "S7",
    "SAS": "SK",
    "Saudia": "SV",
    "Singapore Airlines": "SQ",
    "SkyWest Airlines": "OO",
    "South African Airways": "SA",
    "Southwest Airlines": "WN",
    "Spirit Airlines": "NK",
    "Swiss International Air Lines": "LX",
    "TAP Air Portugal": "TP",
    "Thai Airways": "TG",
    "Turkish Airlines": "TK",
    "United Airlines": "UA",
    "Virgin Atlantic": "VS",
    "Virgin Australia": "VA",
    "Vueling": "VY",
    "WestJet": "WS",
    "Wizz Air": "W6",
}

PRIMARY_AIRLINE_BY_AIRPORT = {
    "ATL": ("DL", "Atlanta is Delta's largest hub."),
    "DTW": ("DL", "Detroit is a major Delta hub."),
    "MSP": ("DL", "Minneapolis-St. Paul is a major Delta hub."),
    "SLC": ("DL", "Salt Lake City is a major Delta hub."),
    "JFK": ("DL", "New York JFK has a large Delta long-haul network."),
    "LGA": ("DL", "LaGuardia has a large Delta domestic network."),
    "SEA": ("AS", "Seattle is Alaska Airlines' main hub."),
    "DFW": ("AA", "Dallas/Fort Worth is American Airlines' largest hub."),
    "CLT": ("AA", "Charlotte is a major American Airlines hub."),
    "MIA": ("AA", "Miami is a major American Airlines hub."),
    "PHL": ("AA", "Philadelphia is a major American Airlines hub."),
    "PHX": ("AA", "Phoenix is a major American Airlines hub."),
    "DCA": ("AA", "Washington National has a large American Airlines presence."),
    "ORD": ("UA", "Chicago O'Hare is a major United Airlines hub."),
    "DEN": ("UA", "Denver is a major United Airlines hub."),
    "EWR": ("UA", "Newark is a major United Airlines hub."),
    "IAD": ("UA", "Washington Dulles is a major United Airlines hub."),
    "IAH": ("UA", "Houston Intercontinental is a major United Airlines hub."),
    "SFO": ("UA", "San Francisco is a major United Airlines hub."),
    "BWI": ("WN", "Baltimore has a large Southwest Airlines network."),
    "MDW": ("WN", "Chicago Midway is a major Southwest Airlines airport."),
    "HOU": ("WN", "Houston Hobby is a major Southwest Airlines airport."),
    "DAL": ("WN", "Dallas Love Field is Southwest Airlines' home airport."),
    "OAK": ("WN", "Oakland has a large Southwest Airlines network."),
    "SJC": ("WN", "San Jose has a large Southwest Airlines network."),
    "FLL": ("B6", "Fort Lauderdale has a large JetBlue network."),
    "BOS": ("B6", "Boston has a large JetBlue network."),
    "HNL": ("HA", "Honolulu is Hawaiian Airlines' main hub."),
    "LHR": ("BA", "London Heathrow is British Airways' main hub."),
    "LGW": ("BA", "London Gatwick has a large British Airways network."),
    "DUB": ("EI", "Dublin is Aer Lingus' main hub."),
    "CDG": ("AF", "Paris Charles de Gaulle is Air France's main hub."),
    "AMS": ("KL", "Amsterdam is KLM's main hub."),
    "FRA": ("LH", "Frankfurt is Lufthansa's main hub."),
    "MUC": ("LH", "Munich is a major Lufthansa hub."),
    "ZRH": ("LX", "Zurich is Swiss International Air Lines' main hub."),
    "MAD": ("IB", "Madrid is Iberia's main hub."),
    "BCN": ("VY", "Barcelona has a large Vueling network."),
    "FCO": ("AZ", "Rome Fiumicino is ITA Airways' main hub."),
    "IST": ("TK", "Istanbul is Turkish Airlines' main hub."),
    "CPH": ("SK", "Copenhagen is a major SAS hub."),
    "OSL": ("SK", "Oslo is a major SAS hub."),
    "ARN": ("SK", "Stockholm Arlanda is a major SAS hub."),
    "HEL": ("AY", "Helsinki is Finnair's main hub."),
    "DXB": ("EK", "Dubai is Emirates' main hub."),
    "AUH": ("EY", "Abu Dhabi is Etihad Airways' main hub."),
    "DOH": ("QR", "Doha is Qatar Airways' main hub."),
    "JED": ("SV", "Jeddah is a major Saudia hub."),
    "RUH": ("SV", "Riyadh is a major Saudia hub."),
    "DEL": ("AI", "Delhi is a major Air India hub."),
    "BOM": ("AI", "Mumbai is a major Air India hub."),
    "BLR": ("AI", "Bengaluru has a large Air India network."),
    "SIN": ("SQ", "Singapore is Singapore Airlines' main hub."),
    "KUL": ("MH", "Kuala Lumpur is Malaysia Airlines' main hub."),
    "BKK": ("TG", "Bangkok is Thai Airways' main hub."),
    "HKG": ("CX", "Hong Kong is Cathay Pacific's main hub."),
    "TPE": ("CI", "Taipei Taoyuan is China Airlines' main hub."),
    "ICN": ("KE", "Seoul Incheon is Korean Air's main hub."),
    "NRT": ("JL", "Tokyo Narita has a large Japan Airlines network."),
    "HND": ("JL", "Tokyo Haneda has a large Japan Airlines network."),
    "KIX": ("JL", "Osaka Kansai has Japan Airlines service."),
    "PVG": ("MU", "Shanghai Pudong is China Eastern's main hub."),
    "PEK": ("CA", "Beijing Capital is Air China's main hub."),
    "CAN": ("CZ", "Guangzhou is China Southern's main hub."),
    "MNL": ("PR", "Manila is Philippine Airlines' main hub."),
    "CGK": ("GA", "Jakarta is Garuda Indonesia's main hub."),
    "SYD": ("QF", "Sydney is a major Qantas hub."),
    "MEL": ("QF", "Melbourne is a major Qantas hub."),
    "BNE": ("QF", "Brisbane is a major Qantas hub."),
    "AKL": ("NZ", "Auckland is Air New Zealand's main hub."),
    "YYZ": ("AC", "Toronto Pearson is Air Canada's largest hub."),
    "YVR": ("AC", "Vancouver is a major Air Canada hub."),
    "YUL": ("AC", "Montreal is a major Air Canada hub."),
    "YYC": ("WS", "Calgary is WestJet's main hub."),
    "MEX": ("AM", "Mexico City is Aeromexico's main hub."),
    "CUN": ("AM", "Cancun has a large Aeromexico network."),
    "GDL": ("AM", "Guadalajara has a large Aeromexico network."),
    "BOG": ("AV", "Bogota is Avianca's main hub."),
    "LIM": ("LA", "Lima has a large LATAM network."),
    "GRU": ("LA", "Sao Paulo Guarulhos has a large LATAM network."),
    "SCL": ("LA", "Santiago has a large LATAM network."),
    "PTY": ("CM", "Panama City is Copa Airlines' main hub."),
    "ADD": ("ET", "Addis Ababa is Ethiopian Airlines' main hub."),
    "NBO": ("KQ", "Nairobi is Kenya Airways' main hub."),
    "JNB": ("SA", "Johannesburg has a large South African Airways network."),
    "CAI": ("MS", "Cairo is Egyptair's main hub."),
}

AIRPORT_FALLBACK = {
    "ATL": ("Atlanta Hartsfield-Jackson", 33.6367, -84.4281),
    "BOS": ("Boston Logan", 42.3656, -71.0096),
    "CLT": ("Charlotte Douglas", 35.2140, -80.9431),
    "DEN": ("Denver", 39.8561, -104.6737),
    "DFW": ("Dallas/Fort Worth", 32.8998, -97.0403),
    "JFK": ("New York JFK", 40.6413, -73.7781),
    "LAS": ("Las Vegas Harry Reid", 36.0840, -115.1537),
    "LAX": ("Los Angeles", 33.9416, -118.4085),
    "MIA": ("Miami", 25.7959, -80.2870),
    "ORD": ("Chicago O'Hare", 41.9742, -87.9073),
    "PHX": ("Phoenix Sky Harbor", 33.4352, -112.0101),
    "SEA": ("Seattle-Tacoma", 47.4502, -122.3088),
    "SFO": ("San Francisco", 37.6213, -122.3790),
}


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


WEATHER_PRESETS = {
    "Clear": {
        "temperature_2m": 24.0,
        "relative_humidity_2m": 45.0,
        "precipitation": 0.0,
        "snow_depth": 0.0,
        "surface_pressure": 1018.0,
        "cloud_cover": 8.0,
        "wind_speed_10m": 8.0,
        "wind_gusts_10m": 12.0,
        "wind_direction": 250,
    },
    "Cloudy": {
        "temperature_2m": 18.0,
        "relative_humidity_2m": 68.0,
        "precipitation": 0.2,
        "snow_depth": 0.0,
        "surface_pressure": 1013.0,
        "cloud_cover": 75.0,
        "wind_speed_10m": 16.0,
        "wind_gusts_10m": 24.0,
        "wind_direction": 230,
    },
    "Rain": {
        "temperature_2m": 17.0,
        "relative_humidity_2m": 86.0,
        "precipitation": 6.0,
        "snow_depth": 0.0,
        "surface_pressure": 1007.0,
        "cloud_cover": 92.0,
        "wind_speed_10m": 24.0,
        "wind_gusts_10m": 38.0,
        "wind_direction": 210,
    },
    "Storm": {
        "temperature_2m": 23.0,
        "relative_humidity_2m": 88.0,
        "precipitation": 18.0,
        "snow_depth": 0.0,
        "surface_pressure": 997.0,
        "cloud_cover": 98.0,
        "wind_speed_10m": 45.0,
        "wind_gusts_10m": 76.0,
        "wind_direction": 205,
    },
    "Snow": {
        "temperature_2m": -4.0,
        "relative_humidity_2m": 82.0,
        "precipitation": 5.0,
        "snow_depth": 0.25,
        "surface_pressure": 1005.0,
        "cloud_cover": 95.0,
        "wind_speed_10m": 24.0,
        "wind_gusts_10m": 42.0,
        "wind_direction": 20,
    },
    "Fog": {
        "temperature_2m": 9.0,
        "relative_humidity_2m": 97.0,
        "precipitation": 0.2,
        "snow_depth": 0.0,
        "surface_pressure": 1011.0,
        "cloud_cover": 100.0,
        "wind_speed_10m": 5.0,
        "wind_gusts_10m": 8.0,
        "wind_direction": 160,
    },
    "Windy": {
        "temperature_2m": 20.0,
        "relative_humidity_2m": 55.0,
        "precipitation": 0.5,
        "snow_depth": 0.0,
        "surface_pressure": 1009.0,
        "cloud_cover": 45.0,
        "wind_speed_10m": 44.0,
        "wind_gusts_10m": 68.0,
        "wind_direction": 275,
    },
}

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "snow_depth",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
]
try:
    AVIATIONSTACK_API_KEY = (os.getenv("AVIATIONSTACK_API_KEY") or st.secrets.get("AVIATIONSTACK_API_KEY", "")).strip()
except (FileNotFoundError, KeyError):
    AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "").strip()
AVIATIONSTACK_FLIGHTS_URL = "https://api.aviationstack.com/v1/flights"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIVOYAGE_API_URL = "https://en.wikivoyage.org/w/api.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
HTTP_HEADERS = {"User-Agent": "FlightDelayPassengerDemo/1.0"}
AIRLINE_AUTO_LABEL = "Auto estimate"
CURRENCY_RATES = {
    "USD": 1.0,
    "IDR": 16200.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "SGD": 1.35,
    "MYR": 4.7,
    "AUD": 1.52,
    "JPY": 157.0,
}
CURRENCY_SYMBOLS = {
    "USD": "$",
    "IDR": "Rp ",
    "EUR": "€",
    "GBP": "£",
    "SGD": "S$",
    "MYR": "RM",
    "AUD": "A$",
    "JPY": "¥",
}
LANGUAGE_COPY = {
    "English": {
        "eyebrow": "Passenger flight delay assistant",
        "title": "Plan smarter before you leave for the airport.",
        "subtitle": "Enter your flight details to estimate delay risk, weather pressure, airport crowding, travel tips, and destination news. In this demo, a delay means the flight is expected to arrive 15 minutes or more later than scheduled.",
        "check": "Check my flight",
        "lookup": "Look up flight and check risk",
    },
    "Bahasa Indonesia": {
        "eyebrow": "Asisten keterlambatan penerbangan",
        "title": "Rencanakan perjalanan sebelum berangkat ke bandara.",
        "subtitle": "Masukkan detail penerbangan untuk melihat risiko delay, cuaca, keramaian bandara, tips perjalanan, dan berita destinasi. Di demo ini, delay berarti penerbangan diperkirakan tiba 15 menit atau lebih lambat dari jadwal.",
        "check": "Cek penerbangan saya",
        "lookup": "Cari penerbangan dan cek risiko",
    },
    "Malay": {
        "eyebrow": "Pembantu kelewatan penerbangan",
        "title": "Rancang perjalanan sebelum ke lapangan terbang.",
        "subtitle": "Masukkan butiran penerbangan untuk anggaran risiko lewat, cuaca, kesesakan lapangan terbang, tip perjalanan, dan berita destinasi. Dalam demo ini, lewat bermaksud tiba 15 minit atau lebih selepas jadual.",
        "check": "Semak penerbangan saya",
        "lookup": "Cari penerbangan dan semak risiko",
    },
    "Chinese": {
        "eyebrow": "旅客航班延误助手",
        "title": "出发去机场前，先把行程计划好。",
        "subtitle": "输入航班信息，查看延误风险、天气、机场繁忙程度、旅行提示和目的地资讯。本演示中，延误表示预计到达时间比计划晚 15 分钟或更久。",
        "check": "检查我的航班",
        "lookup": "查询航班并检查风险",
    },
}

TRAFFIC_PRESETS = {
    "Quiet": {"traffic_level": 0.25, "origin_departures": 250, "dest_arrivals": 250},
    "Normal": {"traffic_level": 0.45, "origin_departures": 550, "dest_arrivals": 550},
    "Busy": {"traffic_level": 0.70, "origin_departures": 900, "dest_arrivals": 900},
    "Very busy": {"traffic_level": 0.92, "origin_departures": 1250, "dest_arrivals": 1250},
}

RECENT_DELAY_PRESETS = {
    "Low": 0.08,
    "Some": 0.18,
    "Many": 0.35,
}

THRESHOLD_MODE_ORDER = ["Recall first", "Balanced", "Precision first"]
THRESHOLD_MODE_TARGETS = {
    "Recall first": 0.15,
    "Balanced": 0.21,
    "Precision first": 0.35,
}
THRESHOLD_MODE_DESCRIPTIONS = {
    "Recall first": "Catches more possible delays, with more false alarms.",
    "Balanced": "Keeps recall and precision in a middle operating range.",
    "Precision first": "Raises confidence before flagging a delay, with fewer false alarms.",
}

NETWORK_CRITICAL_ORIGINS = {"ASE", "BWI", "DAL", "DEN", "DFW", "FLL", "LAS", "MCO", "MDW", "MIA", "EWR"}
NETWORK_CRITICAL_ROUTES = {
    "DEN-OAK",
    "BWI-HOU",
    "BWI-SJU",
    "MDW-LAX",
    "BWI-BUF",
    "DFW-SMF",
    "DFW-MCO",
    "FLL-BOS",
}


HEADER_IMAGE_URI = image_data_uri(HEADER_IMAGE_PATH)

st.set_page_config(page_title="Passenger Flight Delay Assistant", layout="wide")


st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #e0f7ff 0%, #f8fafc 34%, #ffffff 100%);
    }
    .main .block-container {
        max-width: 1220px;
        padding-top: 1.2rem;
    }
    h1, h2, h3 {
        color: #0f766e;
    }
    h4, h5 {
        color: #7c3aed;
    }
    p, li {
        color: #334155;
    }
    div[data-testid="stMetricValue"] {
        color: #0f766e;
    }
    div[data-testid="stFormSubmitButton"] button,
    button[kind="primary"] {
        background: linear-gradient(135deg, #0f766e, #2563eb) !important;
        border: 1px solid #0f766e !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        box-shadow: 0 14px 28px rgba(37, 99, 235, 0.24) !important;
    }
    div[data-testid="stFormSubmitButton"] button p,
    button[kind="primary"] p {
        color: #ffffff !important;
    }
    div.stLinkButton > a,
    div[data-testid="stLinkButton"] a,
    a[data-testid="stLinkButton"] {
        background: linear-gradient(135deg, #f97316, #ec4899) !important;
        border: 1px solid rgba(249, 115, 22, 0.72) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        box-shadow: 0 14px 28px rgba(236, 72, 153, 0.22) !important;
    }
    div.stLinkButton > a p,
    div[data-testid="stLinkButton"] a p,
    a[data-testid="stLinkButton"] p {
        color: #ffffff !important;
    }
    div.stLinkButton > a:hover,
    div[data-testid="stLinkButton"] a:hover,
    a[data-testid="stLinkButton"]:hover {
        filter: brightness(1.04);
        transform: translateY(-1px);
    }
    .hero-banner {
        min-height: 250px;
        border-radius: 8px;
        padding: 32px 34px;
        margin: 0 0 22px 0;
        border: 1px solid rgba(14, 116, 144, 0.18);
        background-image:
            linear-gradient(90deg, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.88) 36%, rgba(255,255,255,0.20) 68%),
            url("__HEADER_IMAGE__");
        background-size: cover;
        background-position: center;
        box-shadow: 0 18px 50px rgba(14, 116, 144, 0.14);
    }
    .hero-eyebrow {
        color: #0f766e;
        font-size: 0.82rem;
        font-weight: 900;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .hero-title {
        max-width: 560px;
        color: #0f172a;
        font-size: 2.65rem;
        line-height: 1.05;
        font-weight: 900;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        max-width: 620px;
        color: #334155;
        font-size: 1.02rem;
        line-height: 1.55;
        font-weight: 600;
    }
    .hero-pill {
        display: inline-block;
        margin: 14px 8px 0 0;
        padding: 8px 11px;
        border-radius: 999px;
        background: #ffffff;
        border: 1px solid #bae6fd;
        color: #075985;
        font-weight: 800;
        font-size: 0.86rem;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    }
    .risk-card {
        background: linear-gradient(135deg, #ffffff 0%, #ecfeff 58%, #fff7ed 100%);
        border: 1px solid #67e8f9;
        border-radius: 8px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 20px 46px rgba(8, 145, 178, 0.14);
    }
    .risk-percent {
        font-size: 56px;
        line-height: 1;
        font-weight: 800;
        color: #0f766e;
        margin: 4px 0 10px 0;
    }
    .risk-label {
        display: inline-block;
        border-radius: 999px;
        padding: 6px 12px;
        font-weight: 700;
        background: #e0f2fe;
        color: #075985;
    }
    .action-box {
        background: #f8fafc;
        border-left: 4px solid #0f766e;
        padding: 12px 14px;
        margin-top: 14px;
    }
    .context-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(240,253,250,0.96));
        border: 1px solid #99f6e4;
        border-radius: 8px;
        padding: 14px 16px;
        min-height: 185px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
    }
    .context-card .label {
        align-items: center;
        color: #0f766e;
        display: flex;
        gap: 10px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .context-card .value {
        color: #7c2d12;
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .context-card .detail {
        color: #475569;
        font-size: 0.9rem;
    }
    .decision-card {
        background: #ffffff;
        border: 1px solid #dbe4ee;
        border-radius: 8px;
        padding: 16px;
        min-height: 150px;
    }
    .decision-card h4 {
        margin: 0 0 8px 0;
        font-size: 1rem;
    }
    .decision-card ul {
        margin: 8px 0 0 18px;
        padding: 0;
    }
    .decision-card li {
        margin: 6px 0;
    }
    .priority-high {
        color: #991b1b;
        font-weight: 800;
    }
    .priority-medium {
        color: #92400e;
        font-weight: 800;
    }
    .priority-normal {
        color: #166534;
        font-weight: 800;
    }
    .journey-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 8px 0 16px 0;
    }
    .journey-step {
        background: #ffffff;
        border: 1px solid #dbe4ee;
        border-radius: 8px;
        padding: 14px 16px;
    }
    .journey-step .kicker {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .journey-step .headline {
        color: #0f172a;
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .journey-step .note {
        color: #475569;
        font-size: 0.92rem;
    }
    .map-note {
        color: #475569;
        margin: 0 0 12px 0;
    }
    .scroll-cue {
        display: block;
        margin: 18px 0 16px 0;
        min-height: 126px;
        padding: 20px 24px;
        border: 1px solid rgba(20, 184, 166, 0.38);
        border-radius: 8px;
        background-image:
            linear-gradient(90deg, rgba(15, 118, 110, 0.94) 0%, rgba(8, 145, 178, 0.82) 48%, rgba(124, 58, 237, 0.58) 100%),
            url("__HEADER_IMAGE__");
        background-size: cover;
        background-position: center;
        color: #ffffff;
        text-decoration: none;
        box-shadow: 0 18px 45px rgba(15, 118, 110, 0.24);
    }
    .scroll-cue:hover {
        color: #ffffff;
        text-decoration: none;
        transform: translateY(-1px);
    }
    .scroll-cue .cue-kicker {
        display: block;
        color: #ccfbf1;
        font-size: 0.78rem;
        font-weight: 900;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .scroll-cue strong {
        display: block;
        color: #ffffff;
        font-size: 1.65rem;
        line-height: 1.1;
    }
    .scroll-cue small {
        display: block;
        color: #f0fdfa;
        font-size: 0.95rem;
        margin-top: 6px;
    }
    .destination-card {
        border: 1px solid #dbe4ee;
        border-radius: 8px;
        padding: 14px 16px;
        background: #ffffff;
        min-height: 120px;
    }
    .destination-card h5 {
        margin: 0 0 8px 0;
        font-size: 1rem;
    }
    .icon-chip {
        display: inline-block;
        margin-right: 6px;
        font-size: 1.1rem;
    }
    .auto-icon {
        align-items: center;
        border-radius: 16px;
        color: #ffffff;
        display: inline-flex;
        flex: 0 0 auto;
        font-size: 1.65rem;
        font-weight: 950;
        height: 54px;
        justify-content: center;
        letter-spacing: 0;
        line-height: 1;
        position: relative;
        width: 54px;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
    }
    .auto-icon::after {
        border: 2px solid rgba(255,255,255,0.55);
        border-radius: 18px;
        content: "";
        inset: 7px;
        position: absolute;
    }
    .icon-clear { background: linear-gradient(135deg, #f59e0b, #f97316); }
    .icon-cloudy { background: linear-gradient(135deg, #06b6d4, #64748b); }
    .icon-rain { background: linear-gradient(135deg, #2563eb, #0ea5e9); }
    .icon-storm { background: linear-gradient(135deg, #7c3aed, #ef4444); }
    .icon-snow { background: linear-gradient(135deg, #38bdf8, #e0f2fe); color: #075985; }
    .icon-fog { background: linear-gradient(135deg, #94a3b8, #475569); }
    .icon-windy { background: linear-gradient(135deg, #14b8a6, #22c55e); }
    .icon-crowd { background: linear-gradient(135deg, #ec4899, #f97316); }
    .icon-quiet { background: linear-gradient(135deg, #14b8a6, #22c55e); }
    .icon-delay { background: linear-gradient(135deg, #dc2626, #facc15); }
    .icon-airline { background: linear-gradient(135deg, #2563eb, #7c3aed); }
    .icon-arrival { background: linear-gradient(135deg, #0f766e, #84cc16); }
    .feed-card {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        background: #ffffff;
        border: 1px solid #dbe4ee;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    }
    .feed-card img {
        width: 58px;
        height: 58px;
        border-radius: 8px;
        object-fit: cover;
        flex: 0 0 auto;
        background: #e0f2fe;
    }
    .feed-title {
        color: #0f172a;
        font-weight: 850;
        line-height: 1.25;
        margin-bottom: 5px;
    }
    .feed-meta {
        color: #64748b;
        font-size: 0.82rem;
    }
    .flight-card {
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        border: 1px solid #bae6fd;
        border-radius: 8px;
        padding: 13px;
        min-height: 150px;
        box-shadow: 0 12px 28px rgba(14, 165, 233, 0.10);
    }
    .flight-card .tag {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 8px;
        background: #ffedd5;
        color: #9a3412;
        font-size: 0.76rem;
        font-weight: 900;
        margin-bottom: 8px;
    }
    .flight-card .airline {
        color: #7c3aed;
        font-size: 1rem;
        font-weight: 900;
        margin-bottom: 4px;
    }
    .flight-card .detail {
        color: #0369a1;
        font-size: 0.88rem;
        margin-bottom: 10px;
    }
    .flight-card .flight-number {
        color: #0f766e;
        font-size: 1.55rem;
        font-weight: 900;
        margin: 4px 0;
    }
    .flight-card .price {
        color: #be123c;
        font-size: 1.18rem;
        font-weight: 950;
        margin-top: 6px;
    }
    .airline-chip {
        background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
        border: 1px solid #c4b5fd;
        border-radius: 8px;
        padding: 12px;
        min-height: 118px;
        box-shadow: 0 10px 24px rgba(124, 58, 237, 0.10);
    }
    .airline-chip .rank {
        color: #f97316;
        font-size: 0.76rem;
        font-weight: 900;
        text-transform: uppercase;
    }
    .airline-chip .name {
        color: #0f766e;
        font-size: 1.05rem;
        font-weight: 950;
        margin: 4px 0;
    }
    .airline-chip .reason {
        color: #475569;
        font-size: 0.88rem;
    }
    .flight-card .time-row {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        border-top: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        padding: 9px 0;
        margin: 10px 0;
    }
    .flight-card .time-row span {
        color: #64748b;
        display: block;
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    .flight-card .time-row strong {
        color: #0f172a;
        display: block;
        font-size: 1.08rem;
    }
    .booking-note {
        color: #64748b;
        font-size: 0.88rem;
        margin: 6px 0 12px 0;
    }
    .hotel-activity-card {
        background: #ffffff;
        border: 1px solid #dbe4ee;
        border-radius: 8px;
        padding: 16px;
        min-height: 230px;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
    }
    .hotel-activity-card h5 {
        margin: 0 0 10px 0;
        font-size: 1rem;
    }
    .hotel-activity-card ul {
        margin: 0 0 14px 18px;
        padding: 0;
    }
    .hotel-activity-card li {
        margin: 7px 0;
    }
    .app-footer {
        background: linear-gradient(135deg, #0f172a 0%, #0f766e 62%, #2563eb 100%);
        border-radius: 8px;
        color: #ffffff;
        margin-top: 30px;
        padding: 26px 28px;
        box-shadow: 0 18px 42px rgba(37, 99, 235, 0.22);
    }
    .footer-grid {
        display: grid;
        grid-template-columns: 1.5fr repeat(3, minmax(0, 1fr));
        gap: 22px;
    }
    .app-footer h4,
    .app-footer h5 {
        color: #ffffff;
        font-size: 1rem;
        margin-bottom: 8px;
    }
    .app-footer p {
        color: #e0f2fe;
        margin: 0 0 10px 0;
        line-height: 1.55;
    }
    .app-footer a {
        color: #fef3c7;
        display: block;
        font-weight: 800;
        margin: 6px 0;
        text-decoration: none;
    }
    .app-footer a:hover {
        color: #ffffff;
        text-decoration: underline;
    }
    .footer-bottom {
        border-top: 1px solid rgba(255,255,255,0.22);
        color: #cbd5e1;
        font-size: 0.86rem;
        margin-top: 18px;
        padding-top: 14px;
    }
    @media (max-width: 800px) {
        .footer-grid {
            grid-template-columns: 1fr;
        }
    }
    @media (max-width: 800px) {
        .hero-banner {
            padding: 24px 20px;
            background-position: center right;
        }
        .hero-title {
            font-size: 2rem;
        }
        .journey-strip {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """.replace("__HEADER_IMAGE__", HEADER_IMAGE_URI),
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_artifact() -> dict:
    artifact = joblib.load(MODEL_PATH)
    repair_sklearn_compatibility(artifact)
    return artifact


def rebuild_split_model_artifact(model_path: Path) -> bool:
    """Rebuild the split model file used to stay under GitHub browser upload limits."""
    if model_path.exists():
        return True

    parts = sorted(model_path.parent.glob(f"{model_path.name}.part-*"))
    if not parts:
        return False

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as output:
        for part in parts:
            output.write(part.read_bytes())
    return model_path.exists()


def repair_sklearn_compatibility(artifact: dict) -> None:
    pipeline = artifact.get("pipeline")
    if pipeline is None or not hasattr(pipeline, "named_steps"):
        return

    for step in pipeline.named_steps.values():
        if step.__class__.__name__ == "SimpleImputer" and not hasattr(step, "_fill_dtype"):
            step._fill_dtype = getattr(step, "statistics_", pd.Series([0.0])).dtype


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_threshold_table() -> pd.DataFrame:
    if not THRESHOLDS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(THRESHOLDS_PATH)


@st.cache_data(show_spinner=False)
def load_airports() -> pd.DataFrame:
    if not AIRPORTS_PATH.exists():
        rows = [
            {
                "iata_code": code,
                "name": values[0],
                "latitude_deg": values[1],
                "longitude_deg": values[2],
                "municipality": values[0],
                "iso_country": "",
            }
            for code, values in AIRPORT_FALLBACK.items()
        ]
        return pd.DataFrame(rows)

    cols = ["iata_code", "name", "latitude_deg", "longitude_deg", "municipality", "iso_country", "scheduled_service"]
    airports = pd.read_csv(AIRPORTS_PATH, usecols=cols)
    airports = airports[
        airports["iata_code"].notna()
        & airports["latitude_deg"].notna()
        & airports["longitude_deg"].notna()
        & (airports["scheduled_service"].fillna("").str.lower() == "yes")
    ].copy()
    airports["iata_code"] = airports["iata_code"].astype(str).str.upper()
    airports = airports[airports["iata_code"].str.fullmatch(r"[A-Z0-9]{3}")].copy()
    airports["name"] = airports["name"].fillna(airports["iata_code"])
    airports["municipality"] = airports["municipality"].fillna("")
    airports["iso_country"] = airports["iso_country"].fillna("")
    return airports.drop_duplicates("iata_code").sort_values("iata_code")


@st.cache_data(show_spinner=False)
def load_airport_catalog() -> pd.DataFrame:
    fallback_rows = [
        {
            "iata_code": code,
            "name": values[0],
            "latitude_deg": values[1],
            "longitude_deg": values[2],
            "municipality": values[0],
            "iso_country": "",
        }
        for code, values in AIRPORT_FALLBACK.items()
    ]
    if not AIRPORTS_PATH.exists():
        return pd.DataFrame(fallback_rows)

    cols = ["iata_code", "name", "latitude_deg", "longitude_deg", "municipality", "iso_country"]
    airports = pd.read_csv(AIRPORTS_PATH, usecols=cols)
    airports = airports[
        airports["iata_code"].notna()
        & airports["latitude_deg"].notna()
        & airports["longitude_deg"].notna()
    ].copy()
    airports["iata_code"] = airports["iata_code"].astype(str).str.upper()
    airports["name"] = airports["name"].fillna(airports["iata_code"])
    airports["municipality"] = airports["municipality"].fillna("")
    airports["iso_country"] = airports["iso_country"].fillna("")
    return airports.drop_duplicates("iata_code")


class WeatherFetchError(Exception):
    pass


class FlightLookupError(Exception):
    pass


class DestinationInfoError(Exception):
    pass


def airport_location(airport_code: str, airports: pd.DataFrame) -> tuple[float, float]:
    matches = airports[airports["iata_code"] == airport_code]
    if matches.empty:
        catalog = load_airport_catalog()
        matches = catalog[catalog["iata_code"] == airport_code]
    if matches.empty:
        fallback = AIRPORT_FALLBACK.get(airport_code)
        if fallback is None:
            raise WeatherFetchError(f"No coordinates found for {airport_code}.")
        return float(fallback[1]), float(fallback[2])

    row = matches.iloc[0]
    return float(row["latitude_deg"]), float(row["longitude_deg"])


def weather_endpoint_for(flight_date: date) -> str:
    today = date.today()
    if flight_date < today:
        return OPEN_METEO_ARCHIVE_URL
    if flight_date <= today + timedelta(days=15):
        return OPEN_METEO_FORECAST_URL
    raise WeatherFetchError("Open-Meteo forecast data is available for roughly the next 15 days.")


def nearest_hour_index(times: list[str], target: datetime) -> int:
    parsed_times = [datetime.fromisoformat(value) for value in times]
    return min(range(len(parsed_times)), key=lambda index: abs(parsed_times[index] - target))


def weather_condition_name(weather: dict[str, float]) -> str:
    temperature = weather["temperature_2m"]
    precipitation = weather["precipitation"]
    cloud_cover = weather["cloud_cover"]
    humidity = weather["relative_humidity_2m"]
    wind_speed = weather["wind_speed_10m"]
    wind_gust = weather["wind_gusts_10m"]
    snow_depth = weather["snow_depth"]

    if snow_depth > 0.03 or (temperature <= 1 and precipitation >= 0.5):
        return "Snow"
    if wind_gust >= 60 or precipitation >= 12:
        return "Storm"
    if precipitation >= 1:
        return "Rain"
    if humidity >= 94 and cloud_cover >= 85 and wind_speed <= 10:
        return "Fog"
    if wind_speed >= 35:
        return "Windy"
    if cloud_cover >= 60:
        return "Cloudy"
    return "Clear"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_open_meteo_weather(
    airport_code: str,
    latitude: float,
    longitude: float,
    flight_date: date,
    departure_hour: int,
) -> dict[str, object]:
    endpoint = weather_endpoint_for(flight_date)
    params = {
        "latitude": f"{latitude:.5f}",
        "longitude": f"{longitude:.5f}",
        "hourly": ",".join(OPEN_METEO_HOURLY_FIELDS),
        "start_date": flight_date.isoformat(),
        "end_date": flight_date.isoformat(),
        "timezone": "auto",
        "wind_speed_unit": "kmh",
    }
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"

    last_error: Exception | None = None
    for _ in range(2):
        try:
            request = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
    else:
        reason = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown network error"
        raise WeatherFetchError(f"Weather API request failed for {airport_code}. Render or Open-Meteo could not complete the request ({reason}).")

    if payload.get("error"):
        raise WeatherFetchError(str(payload.get("reason", "Weather API returned an error.")))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise WeatherFetchError(f"No hourly weather data returned for {airport_code}.")

    target = datetime.combine(flight_date, time(hour=int(departure_hour)))
    index = nearest_hour_index(times, target)
    values = {}
    fallback = WEATHER_PRESETS["Cloudy"]
    for field in OPEN_METEO_HOURLY_FIELDS:
        key = "wind_direction" if field == "wind_direction_10m" else field
        series = hourly.get(field) or []
        value = series[index] if index < len(series) else None
        values[key] = float(value) if value is not None else float(fallback[key])

    return {
        "airport": airport_code,
        "source": "Open-Meteo forecast" if endpoint == OPEN_METEO_FORECAST_URL else "Open-Meteo archive",
        "timestamp": times[index],
        "condition": weather_condition_name(values),
        "values": values,
    }


def extract_nested(data: dict, path: list[str]) -> str:
    value: object = data
    for key in path:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return str(value or "").strip()


def request_text(url: str, timeout: int = 10) -> str:
    request = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def request_json(url: str, timeout: int = 10) -> dict:
    return json.loads(request_text(url, timeout=timeout))


LANGUAGE_TARGET_CODES = {
    "English": "en",
    "Bahasa Indonesia": "id",
    "Malay": "ms",
    "Chinese": "zh-CN",
}
TRANSLATABLE_STREAMLIT_METHODS = [
    "markdown",
    "caption",
    "info",
    "success",
    "warning",
    "error",
    "subheader",
    "header",
    "title",
    "write",
]
TRANSLATABLE_LABEL_METHODS = [
    "link_button",
    "form_submit_button",
    "button",
    "metric",
    "text_input",
    "number_input",
    "date_input",
    "time_input",
    "checkbox",
    "slider",
    "download_button",
]
TRANSLATABLE_OPTION_METHODS = ["radio", "selectbox"]
TRANSLATABLE_CONTAINER_METHODS = ["expander"]
TRANSLATABLE_CAPTION_METHODS = ["image"]
_TRANSLATION_PATCHED = False
_ORIGINAL_DELTA_METHODS: dict[str, object] = {}
_ORIGINAL_ST_METHODS: dict[str, object] = {}


def selected_language_code(language: str) -> str:
    return LANGUAGE_TARGET_CODES.get(language, "en")


def should_translate_piece(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if not re.search(r"[A-Za-z]", stripped):
        return False
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return False
    return True


@st.cache_data(ttl=604800, show_spinner=False)
def translate_plain_text(value: str, target_code: str) -> str:
    if target_code == "en" or not should_translate_piece(value):
        return value
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_code,
        "dt": "t",
        "q": value,
    }
    url = f"https://translate.googleapis.com/translate_a/single?{urllib.parse.urlencode(params)}"
    try:
        payload = request_json(url, timeout=5)
        translated = "".join(str(part[0]) for part in payload[0] if part and part[0])
        return translated or value
    except Exception:
        return value


@st.cache_data(ttl=604800, show_spinner=False)
def translate_many_plain_text(values: tuple[str, ...], target_code: str) -> tuple[str, ...]:
    if target_code == "en":
        return values
    indexes = [index for index, value in enumerate(values) if should_translate_piece(value)]
    if not indexes:
        return values
    separator = "|||123456789|||"
    joined = f"\n{separator}\n".join(values[index] for index in indexes)
    translated_joined = translate_plain_text(joined, target_code)
    translated_parts = [part.strip("\n") for part in translated_joined.split(separator)]
    if len(translated_parts) != len(indexes):
        translated_parts = [translate_plain_text(values[index], target_code) for index in indexes]
    result = list(values)
    for index, translated in zip(indexes, translated_parts):
        result[index] = translated
    return tuple(result)


def translate_markdown_links(value: str, target_code: str) -> str:
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def repl(match: re.Match[str]) -> str:
        label = translate_plain_text(match.group(1), target_code)
        return f"[{label}]({match.group(2)})"

    return pattern.sub(repl, value)


def translate_markdown_line(value: str, target_code: str) -> str:
    match = re.match(r"^(\s*(?:#{1,6}\s+|[-*]\s+|\d+\.\s+|>\s+)?)(.*)$", value)
    if not match:
        return translate_plain_text(value, target_code)
    prefix, content = match.groups()
    if not content.strip():
        return value
    translated = translate_plain_text(content, target_code)
    return f"{prefix}{translated}"


def translate_markdown_text(value: str, language: str) -> str:
    target_code = selected_language_code(language)
    if target_code == "en" or not isinstance(value, str):
        return value
    value = translate_markdown_links(value, target_code)
    if "\n" in value:
        return "\n".join(translate_markdown_text(line, language) for line in value.splitlines())
    match = re.match(r"^(\s*(?:#{1,6}\s+|[-*]\s+|\d+\.\s+|>\s+)?)(.*)$", value)
    prefix = match.group(1) if match else ""
    content = match.group(2) if match else value
    pieces = re.split(r"(\[[^\]]+\]\([^)]+\)|https?://\S+|`[^`]+`)", value)
    translated: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if piece.startswith("[") or piece.startswith("http") or piece.startswith("`"):
            translated.append(piece)
        else:
            translated.append(translate_plain_text(piece if not prefix else piece.removeprefix(prefix), target_code))
    return prefix + "".join(translated).removeprefix(prefix)


def translate_html_text(value: str, language: str) -> str:
    target_code = selected_language_code(language)
    if target_code == "en" or not isinstance(value, str):
        return value
    pieces = re.split(r"(<[^>]+>)", value)
    text_indexes: list[int] = []
    text_values: list[str] = []
    for index, piece in enumerate(pieces):
        if not piece or (piece.startswith("<") and piece.endswith(">")):
            continue
        if "&" in piece and not re.search(r"[A-Za-z]{3,}", piece):
            continue
        text_indexes.append(index)
        text_values.append(piece)
    translated_values = translate_many_plain_text(tuple(text_values), target_code)
    for index, translated in zip(text_indexes, translated_values):
        pieces[index] = translated
    return "".join(pieces)


def translate_body(value: object, language: str, unsafe_allow_html: bool = False) -> object:
    if not isinstance(value, str):
        return value
    if unsafe_allow_html or "<" in value and ">" in value:
        return translate_html_text(value, language)
    return translate_markdown_text(value, language)


def translate_dataframe(data: pd.DataFrame, language: str) -> pd.DataFrame:
    if selected_language_code(language) == "en" or data.empty:
        return data
    translated = data.copy()
    translated.columns = [translate_markdown_text(str(column), language) for column in translated.columns]
    for column in translated.columns:
        if translated[column].dtype == "object":
            translated[column] = translated[column].map(
                lambda value: translate_markdown_text(value, language) if isinstance(value, str) else value
            )
    return translated


def install_page_translation(language: str) -> None:
    global _TRANSLATION_PATCHED
    if _TRANSLATION_PATCHED:
        return
    _TRANSLATION_PATCHED = True

    for method_name in TRANSLATABLE_STREAMLIT_METHODS:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        _ORIGINAL_DELTA_METHODS[method_name] = original

        def make_text_wrapper(name: str, orig):
            def wrapper(self, body=None, *args, **kwargs):
                if st.session_state.get("_translation_pretranslated", False):
                    return orig(self, body, *args, **kwargs)
                active_language = st.session_state.get("page_language", "English")
                unsafe = bool(kwargs.get("unsafe_allow_html", False))
                return orig(self, translate_body(body, active_language, unsafe), *args, **kwargs)

            return wrapper

        setattr(DeltaGenerator, method_name, make_text_wrapper(method_name, original))

        module_original = getattr(st, method_name, None)
        if module_original is not None:
            _ORIGINAL_ST_METHODS[method_name] = module_original

            def make_module_text_wrapper(name: str, orig):
                def wrapper(body=None, *args, **kwargs):
                    active_language = st.session_state.get("page_language", "English")
                    unsafe = bool(kwargs.get("unsafe_allow_html", False))
                    st.session_state._translation_pretranslated = True
                    try:
                        return orig(translate_body(body, active_language, unsafe), *args, **kwargs)
                    finally:
                        st.session_state._translation_pretranslated = False

                return wrapper

            setattr(st, method_name, make_module_text_wrapper(method_name, module_original))

    for method_name in TRANSLATABLE_LABEL_METHODS:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        _ORIGINAL_DELTA_METHODS[method_name] = original

        def make_label_wrapper(name: str, orig):
            def wrapper(self, label=None, *args, **kwargs):
                if st.session_state.get("_translation_pretranslated", False):
                    return orig(self, label, *args, **kwargs)
                active_language = st.session_state.get("page_language", "English")
                translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                return orig(self, translated_label, *args, **kwargs)

            return wrapper

        setattr(DeltaGenerator, method_name, make_label_wrapper(method_name, original))

        module_original = getattr(st, method_name, None)
        if module_original is not None:
            _ORIGINAL_ST_METHODS[method_name] = module_original

            def make_module_label_wrapper(name: str, orig):
                def wrapper(label=None, *args, **kwargs):
                    active_language = st.session_state.get("page_language", "English")
                    translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                    st.session_state._translation_pretranslated = True
                    try:
                        return orig(translated_label, *args, **kwargs)
                    finally:
                        st.session_state._translation_pretranslated = False

                return wrapper

            setattr(st, method_name, make_module_label_wrapper(method_name, module_original))

    for method_name in TRANSLATABLE_OPTION_METHODS:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        _ORIGINAL_DELTA_METHODS[method_name] = original

        def make_option_wrapper(name: str, orig):
            def wrapper(self, label=None, options=None, *args, **kwargs):
                if st.session_state.get("_translation_pretranslated", False):
                    return orig(self, label, options, *args, **kwargs)
                active_language = st.session_state.get("page_language", "English")
                translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                original_format_func = kwargs.get("format_func")
                try:
                    option_count = len(options) if options is not None else len(kwargs.get("options", []))
                except TypeError:
                    option_count = 0

                def translated_format_func(option):
                    display_value = original_format_func(option) if original_format_func else option
                    if option_count > 120:
                        return display_value
                    if isinstance(display_value, str):
                        return translate_markdown_text(display_value, active_language)
                    return display_value

                kwargs["format_func"] = translated_format_func
                return orig(self, translated_label, options, *args, **kwargs)

            return wrapper

        setattr(DeltaGenerator, method_name, make_option_wrapper(method_name, original))

        module_original = getattr(st, method_name, None)
        if module_original is not None:
            _ORIGINAL_ST_METHODS[method_name] = module_original

            def make_module_option_wrapper(name: str, orig):
                def wrapper(label=None, options=None, *args, **kwargs):
                    active_language = st.session_state.get("page_language", "English")
                    translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                    original_format_func = kwargs.get("format_func")
                    try:
                        option_count = len(options) if options is not None else len(kwargs.get("options", []))
                    except TypeError:
                        option_count = 0

                    def translated_format_func(option):
                        display_value = original_format_func(option) if original_format_func else option
                        if option_count > 120:
                            return display_value
                        if isinstance(display_value, str):
                            return translate_markdown_text(display_value, active_language)
                        return display_value

                    kwargs["format_func"] = translated_format_func
                    st.session_state._translation_pretranslated = True
                    try:
                        return orig(translated_label, options, *args, **kwargs)
                    finally:
                        st.session_state._translation_pretranslated = False

                return wrapper

            setattr(st, method_name, make_module_option_wrapper(method_name, module_original))

    for method_name in TRANSLATABLE_CONTAINER_METHODS:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        _ORIGINAL_DELTA_METHODS[method_name] = original

        def make_container_wrapper(name: str, orig):
            def wrapper(self, label=None, *args, **kwargs):
                if st.session_state.get("_translation_pretranslated", False):
                    return orig(self, label, *args, **kwargs)
                active_language = st.session_state.get("page_language", "English")
                translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                return orig(self, translated_label, *args, **kwargs)

            return wrapper

        setattr(DeltaGenerator, method_name, make_container_wrapper(method_name, original))

        module_original = getattr(st, method_name, None)
        if module_original is not None:
            _ORIGINAL_ST_METHODS[method_name] = module_original

            def make_module_container_wrapper(name: str, orig):
                def wrapper(label=None, *args, **kwargs):
                    active_language = st.session_state.get("page_language", "English")
                    translated_label = translate_markdown_text(label, active_language) if isinstance(label, str) else label
                    st.session_state._translation_pretranslated = True
                    try:
                        return orig(translated_label, *args, **kwargs)
                    finally:
                        st.session_state._translation_pretranslated = False

                return wrapper

            setattr(st, method_name, make_module_container_wrapper(method_name, module_original))

    for method_name in TRANSLATABLE_CAPTION_METHODS:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        _ORIGINAL_DELTA_METHODS[method_name] = original

        def make_caption_wrapper(name: str, orig):
            def wrapper(self, image, *args, **kwargs):
                if st.session_state.get("_translation_pretranslated", False):
                    return orig(self, image, *args, **kwargs)
                active_language = st.session_state.get("page_language", "English")
                caption = kwargs.get("caption")
                if isinstance(caption, str):
                    kwargs["caption"] = translate_markdown_text(caption, active_language)
                return orig(self, image, *args, **kwargs)

            return wrapper

        setattr(DeltaGenerator, method_name, make_caption_wrapper(method_name, original))

        module_original = getattr(st, method_name, None)
        if module_original is not None:
            _ORIGINAL_ST_METHODS[method_name] = module_original

            def make_module_caption_wrapper(name: str, orig):
                def wrapper(image, *args, **kwargs):
                    active_language = st.session_state.get("page_language", "English")
                    caption = kwargs.get("caption")
                    if isinstance(caption, str):
                        kwargs["caption"] = translate_markdown_text(caption, active_language)
                    st.session_state._translation_pretranslated = True
                    try:
                        return orig(image, *args, **kwargs)
                    finally:
                        st.session_state._translation_pretranslated = False

                return wrapper

            setattr(st, method_name, make_module_caption_wrapper(method_name, module_original))

    original_tabs = getattr(DeltaGenerator, "tabs", None)
    if original_tabs is not None:
        _ORIGINAL_DELTA_METHODS["tabs"] = original_tabs

        def tabs_wrapper(self, tabs, *args, **kwargs):
            if st.session_state.get("_translation_pretranslated", False):
                return original_tabs(self, tabs, *args, **kwargs)
            active_language = st.session_state.get("page_language", "English")
            translated_tabs = [translate_markdown_text(str(tab), active_language) for tab in tabs]
            return original_tabs(self, translated_tabs, *args, **kwargs)

        setattr(DeltaGenerator, "tabs", tabs_wrapper)

        module_original_tabs = getattr(st, "tabs", None)
        if module_original_tabs is not None:
            _ORIGINAL_ST_METHODS["tabs"] = module_original_tabs

            def module_tabs_wrapper(tabs, *args, **kwargs):
                active_language = st.session_state.get("page_language", "English")
                translated_tabs = [translate_markdown_text(str(tab), active_language) for tab in tabs]
                st.session_state._translation_pretranslated = True
                try:
                    return module_original_tabs(translated_tabs, *args, **kwargs)
                finally:
                    st.session_state._translation_pretranslated = False

            setattr(st, "tabs", module_tabs_wrapper)


class PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


class ListingNameParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_depth = 0
        self._buffer: list[str] = []
        self.names: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = dict(attrs).get("class") or ""
        if "listing-name" in classes:
            self._capture_depth = 1
            self._buffer = []
        elif self._capture_depth:
            self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self._capture_depth:
            return
        self._capture_depth -= 1
        if self._capture_depth == 0:
            name = " ".join("".join(self._buffer).split())
            if name and name not in self.names:
                self.names.append(name)
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_depth:
            self._buffer.append(data)


def strip_html(value: str) -> str:
    parser = PlainTextParser()
    parser.feed(value)
    return " ".join(parser.text().split())


def parse_api_time(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return value[-8:-3] if len(value) >= 16 else ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_flight_by_number(flight_number: str) -> dict[str, str]:
    if not AVIATIONSTACK_API_KEY:
        raise FlightLookupError("Flight-number lookup needs AVIATIONSTACK_API_KEY to be set.")

    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "flight_iata": flight_number.strip().upper().replace(" ", ""),
        "limit": "5",
    }
    url = f"{AVIATIONSTACK_FLIGHTS_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FlightLookupError("Flight lookup API request failed.") from exc

    if payload.get("error"):
        error = payload["error"]
        raise FlightLookupError(str(error.get("message") or error.get("info") or "Flight lookup API returned an error."))

    flights = payload.get("data") or []
    if not flights:
        raise FlightLookupError("No live or recent flight was found for that flight number.")

    flight = flights[0]
    departure_time = extract_nested(flight, ["departure", "scheduled"]) or extract_nested(flight, ["departure", "estimated"])
    arrival_time = extract_nested(flight, ["arrival", "scheduled"]) or extract_nested(flight, ["arrival", "estimated"])

    return {
        "origin": extract_nested(flight, ["departure", "iata"]),
        "dest": extract_nested(flight, ["arrival", "iata"]),
        "airline": extract_nested(flight, ["airline", "iata"]),
        "flight_number": extract_nested(flight, ["flight", "iata"]),
        "tail_number": extract_nested(flight, ["aircraft", "registration"]),
        "departure_time": parse_api_time(departure_time),
        "arrival_time": parse_api_time(arrival_time),
        "status": extract_nested(flight, ["flight_status"]),
        "source": "Aviationstack",
    }


def flight_details_from_payload(flight: dict, source: str) -> dict[str, str]:
    departure_time = extract_nested(flight, ["departure", "scheduled"]) or extract_nested(flight, ["departure", "estimated"])
    arrival_time = extract_nested(flight, ["arrival", "scheduled"]) or extract_nested(flight, ["arrival", "estimated"])

    return {
        "origin": extract_nested(flight, ["departure", "iata"]),
        "dest": extract_nested(flight, ["arrival", "iata"]),
        "airline": extract_nested(flight, ["airline", "iata"]),
        "flight_number": extract_nested(flight, ["flight", "iata"]),
        "tail_number": extract_nested(flight, ["aircraft", "registration"]),
        "departure_time": parse_api_time(departure_time),
        "arrival_time": parse_api_time(arrival_time),
        "status": extract_nested(flight, ["flight_status"]),
        "source": source,
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_flight_by_tail_best_effort(tail_number: str) -> dict[str, str]:
    if not AVIATIONSTACK_API_KEY:
        raise FlightLookupError("Aircraft registration lookup needs AVIATIONSTACK_API_KEY to be set.")

    target = tail_number.strip().upper().replace(" ", "")
    if not target:
        raise FlightLookupError("Enter a flight number or aircraft tail number.")

    for offset in (0, 100, 200):
        params = {
            "access_key": AVIATIONSTACK_API_KEY,
            "limit": "100",
            "offset": str(offset),
        }
        url = f"{AVIATIONSTACK_FLIGHTS_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise FlightLookupError("Aircraft registration lookup API request failed.") from exc

        if payload.get("error"):
            error = payload["error"]
            raise FlightLookupError(str(error.get("message") or error.get("info") or "Flight lookup API returned an error."))

        for flight in payload.get("data") or []:
            registration = extract_nested(flight, ["aircraft", "registration"]).upper().replace(" ", "")
            if registration == target:
                return flight_details_from_payload(flight, "Aviationstack live feed registration match")

    raise FlightLookupError(
        "No current flight was found for that aircraft registration in Aviationstack's live feed. "
        "Try route/date/time, or use a flight number such as AA100."
    )


def looks_like_flight_number(value: str) -> bool:
    compact = value.strip().upper().replace(" ", "")
    return len(compact) >= 3 and compact[:2].isalnum() and compact[2:].isdigit()


def fetch_flight_by_identifier(identifier: str) -> dict[str, str]:
    value = identifier.strip().upper().replace(" ", "")
    if not value:
        raise FlightLookupError("Enter a flight number or aircraft tail number.")

    if looks_like_flight_number(value):
        try:
            return fetch_flight_by_number(value)
        except FlightLookupError:
            return fetch_flight_by_tail_best_effort(value)

    return fetch_flight_by_tail_best_effort(value)


def airline_name_from_code(code: str) -> str:
    for name, airline_code in AIRLINES.items():
        if airline_code == code:
            return name
    return code


def estimate_airline(origin: str, dest: str) -> tuple[str, str]:
    for airport_code, side in [(origin, "departure"), (dest, "destination")]:
        if airport_code in PRIMARY_AIRLINE_BY_AIRPORT:
            airline_code, reason = PRIMARY_AIRLINE_BY_AIRPORT[airport_code]
            return airline_code, f"Auto-estimated from the {side} airport: {reason}"

    if origin in {"LAX", "LAS", "SFO", "SEA", "SAN", "PDX"} and dest in {"HNL", "OGG", "KOA", "LIH"}:
        return "HA", "Auto-estimated because this looks like a Hawaii route."
    if origin in {"LAX", "SFO", "SEA", "YVR"} and dest in {"NRT", "HND", "KIX", "ICN", "HKG", "TPE"}:
        return "UA", "Auto-estimated from a common transpacific network pattern."
    if origin in {"JFK", "EWR", "BOS", "IAD"} and dest in {"LHR", "CDG", "AMS", "FRA", "DUB"}:
        return "UA", "Auto-estimated from a common transatlantic network pattern."

    return "AA", "Auto-estimated default because no strong airline hub matched this route."


def resolve_airline(airline_choice: str, origin: str, dest: str, lookup_airline: str = "") -> tuple[str, str]:
    lookup_airline = lookup_airline.upper().strip()
    if lookup_airline:
        return lookup_airline, f"Loaded from flight lookup: {airline_name_from_code(lookup_airline)}."
    if airline_choice != AIRLINE_AUTO_LABEL:
        return AIRLINES[airline_choice], "Entered by user."
    return estimate_airline(origin, dest)


def estimate_operational_context(
    origin: str,
    dest: str,
    flight_date: date,
    departure_time: time,
    weather: dict[str, float],
) -> dict[str, str | float]:
    hour = int(departure_time.hour)
    busy_airports = {"ATL", "DFW", "DEN", "ORD", "LAX", "JFK", "CLT", "LAS", "MCO", "SFO", "EWR"}
    very_busy_airports = {"ATL", "DFW", "DEN", "ORD", "LAX", "JFK"}

    if origin in very_busy_airports and hour in {7, 8, 9, 16, 17, 18, 19}:
        traffic_name = "Very busy"
    elif origin in busy_airports or dest in busy_airports or hour in {7, 8, 9, 16, 17, 18, 19}:
        traffic_name = "Busy"
    elif hour < 6 or hour > 22:
        traffic_name = "Quiet"
    else:
        traffic_name = "Normal"

    weather_pressure = 0
    if weather["precipitation"] >= 8 or weather["snow_depth"] >= 0.05:
        weather_pressure += 2
    elif weather["precipitation"] >= 1:
        weather_pressure += 1
    if weather["wind_gusts_10m"] >= 55 or weather["wind_speed_10m"] >= 35:
        weather_pressure += 2
    elif weather["wind_speed_10m"] >= 24:
        weather_pressure += 1
    if weather["cloud_cover"] >= 90 and weather["relative_humidity_2m"] >= 90:
        weather_pressure += 1
    if traffic_name in {"Busy", "Very busy"}:
        weather_pressure += 1
    if holiday_flags(flight_date)["IS_NEAR_HOLIDAY"]:
        weather_pressure += 1

    if weather_pressure >= 4:
        recent_delay_name = "Many"
    elif weather_pressure >= 2:
        recent_delay_name = "Some"
    else:
        recent_delay_name = "Low"

    return {
        "traffic_name": traffic_name,
        "recent_delay_name": recent_delay_name,
        "traffic_source": f"Estimated from {origin}/{dest} hub size and {hour:02d}:00 departure time.",
        "recent_delay_source": "Estimated from weather severity, peak-time pressure, and holiday proximity.",
    }


def airport_label_map(airports: pd.DataFrame) -> dict[str, str]:
    labels = {}
    for _, row in airports.iterrows():
        code = str(row["iata_code"])
        labels[f"{code} - {row['name']}"] = code
    return labels


def threshold_modes(default_threshold: float) -> dict[str, dict[str, float | str | None]]:
    table = load_threshold_table()
    modes = {}
    for name in THRESHOLD_MODE_ORDER:
        target = default_threshold if name == "Balanced" else THRESHOLD_MODE_TARGETS[name]
        mode = {
            "threshold": float(target),
            "precision": None,
            "recall": None,
            "f1": None,
            "false_positive_rate": None,
            "description": THRESHOLD_MODE_DESCRIPTIONS[name],
        }
        if not table.empty and "threshold" in table.columns:
            row = table.iloc[(table["threshold"] - target).abs().idxmin()]
            for key in ["threshold", "precision", "recall", "f1", "false_positive_rate"]:
                if key in row:
                    mode[key] = float(row[key])
        modes[name] = mode
    return modes


def percent_text(value: float | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.{decimals}%}"


def haversine_miles(origin: str, dest: str, airports: pd.DataFrame) -> float:
    lookup = airports.set_index("iata_code")
    if origin not in lookup.index or dest not in lookup.index:
        return 500.0
    o = lookup.loc[origin]
    d = lookup.loc[dest]
    lat1 = math.radians(float(o["latitude_deg"]))
    lon1 = math.radians(float(o["longitude_deg"]))
    lat2 = math.radians(float(d["latitude_deg"]))
    lon2 = math.radians(float(d["longitude_deg"]))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def distance_group(distance_miles: float) -> int:
    return int(max(1, min(11, math.ceil(distance_miles / 250))))


def dep_time_slot(hour: int) -> str:
    if 5 <= hour <= 11:
        return "Morning"
    if 12 <= hour <= 16:
        return "Afternoon"
    if 17 <= hour <= 21:
        return "Evening"
    return "Night"


def season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Fall"


def holiday_flags(flight_date: date) -> dict[str, int]:
    fixed_holidays = {(1, 1), (7, 4), (11, 11), (12, 24), (12, 25), (12, 31)}
    month_day = (flight_date.month, flight_date.day)
    near_holiday = int(
        month_day in fixed_holidays
        or (flight_date.month == 11 and 20 <= flight_date.day <= 30)
        or (flight_date.month == 12 and 20 <= flight_date.day <= 31)
    )
    return {
        "IS_HOLIDAY": int(month_day in fixed_holidays),
        "IS_NEAR_HOLIDAY": near_holiday,
        "IS_PEAK_TRAVEL": int(flight_date.month in (6, 7, 8, 11, 12)),
        "IS_SUMMER_BREAK": int(flight_date.month in (6, 7, 8)),
        "IS_WINTER_BREAK": int(flight_date.month in (12, 1)),
        "IS_SPRING_BREAK": int(flight_date.month == 3),
        "IS_SCHOOL_BREAK": int(flight_date.month in (3, 6, 7, 8, 12, 1)),
    }


def build_feature_row(
    flight_date: date,
    departure_time: time,
    airline_code: str,
    origin: str,
    dest: str,
    weather: dict[str, float],
    traffic_name: str,
    recent_delay_name: str,
    airports: pd.DataFrame,
) -> pd.DataFrame:
    hour = int(departure_time.hour)
    distance = haversine_miles(origin, dest, airports)
    traffic = TRAFFIC_PRESETS[traffic_name]
    wind_rad = math.radians(weather["wind_direction"])
    row = {
        "Year": flight_date.year,
        "Quarter": int(math.ceil(flight_date.month / 3)),
        "Month": flight_date.month,
        "DayofMonth": flight_date.day,
        "DayOfWeek": int(flight_date.isoweekday()),
        "CRSDepHour": hour,
        "is_peak_hour": int(hour in (7, 8, 9, 16, 17, 18, 19)),
        "Distance": round(distance, 1),
        "DistanceGroup": distance_group(distance),
        "Origin": origin,
        "Dest": dest,
        "Operating_Airline": airline_code,
        "ROUTE": f"{origin}-{dest}",
        "Origin_freq": traffic["origin_departures"],
        "Dest_freq": traffic["dest_arrivals"],
        "IS_WEEKEND": int(flight_date.weekday() >= 5),
        "prev_delay": RECENT_DELAY_PRESETS[recent_delay_name],
        "traffic_level": traffic["traffic_level"],
        "temperature_2m": weather["temperature_2m"],
        "relative_humidity_2m": weather["relative_humidity_2m"],
        "precipitation": weather["precipitation"],
        "snow_depth": weather["snow_depth"],
        "surface_pressure": weather["surface_pressure"],
        "cloud_cover": weather["cloud_cover"],
        "wind_speed_10m": weather["wind_speed_10m"],
        "wind_gusts_10m": weather["wind_gusts_10m"],
        "wind_dir_sin": math.sin(wind_rad),
        "wind_dir_cos": math.cos(wind_rad),
    }
    row.update(holiday_flags(flight_date))

    for code in ["9E", "AA", "AS", "B6", "C5", "DL", "F9", "G4", "G7", "HA", "MQ", "NK", "OH", "OO", "PT", "QX", "UA", "WN", "YV", "YX", "ZW"]:
        row[f"Operating_Airline_{code}"] = int(code == airline_code)

    for slot in ["Afternoon", "Evening", "Morning", "Night"]:
        row[f"DEP_TIME_SLOT_{slot}"] = int(slot == dep_time_slot(hour))

    for name in ["Fall", "Spring", "Summer", "Winter"]:
        row[f"SEASON_{name}"] = int(name == season(flight_date.month))

    return pd.DataFrame([row])


def score_frame(artifact: dict, frame: pd.DataFrame, threshold: float) -> pd.DataFrame:
    probabilities = artifact["pipeline"].predict_proba(frame.copy())[:, 1]
    result = frame.copy()
    result["delay_probability"] = probabilities
    result["predicted_delay"] = (probabilities >= threshold).astype(int)
    return result


def risk_label(probability: float, threshold: float) -> str:
    low_cutoff = min(0.15, threshold * 0.7)
    high_cutoff = min(0.75, threshold + 0.15)
    if probability < low_cutoff:
        return "Low risk"
    if probability < threshold:
        return "Moderate risk"
    if probability < high_cutoff:
        return "Delay likely"
    return "High risk"


def action_text(label: str) -> str:
    if label in {"Delay likely", "High risk"}:
        return "Check flight updates early, allow extra time, and watch for gate or crew schedule changes."
    if label == "Moderate risk":
        return "The flight has some delay pressure. Keep alerts on and re-check closer to departure."
    return "The flight looks reasonably stable, but keep normal flight alerts switched on."


def risk_tier(probability: float, threshold: float) -> str:
    if probability >= max(0.35, threshold + 0.12):
        return "High"
    if probability >= threshold:
        return "Elevated"
    if probability >= max(0.12, threshold * 0.7):
        return "Watch"
    return "Low"


def is_network_critical(origin: str, dest: str, hour: int, traffic_name: str) -> bool:
    route = f"{origin}-{dest}"
    return (
        route in NETWORK_CRITICAL_ROUTES
        or origin in NETWORK_CRITICAL_ORIGINS
        or traffic_name in {"Busy", "Very busy"}
        or hour in {7, 8, 9, 16, 17, 18, 19, 20}
    )


def row_network_critical(row: pd.Series) -> bool:
    try:
        hour = int(row.get("CRSDepHour", -1))
    except (TypeError, ValueError):
        hour = -1
    origin = str(row.get("Origin", ""))
    dest = str(row.get("Dest", ""))
    return is_network_critical(origin, dest, hour, "Normal")


def airport_priority(probability: float, threshold: float, network_critical: bool) -> str:
    tier = risk_tier(probability, threshold)
    if tier == "High" or (tier == "Elevated" and network_critical):
        return "High"
    if tier in {"Elevated", "Watch"} or network_critical:
        return "Medium"
    return "Normal"


def passenger_focus(probability: float, threshold: float) -> str:
    tier = risk_tier(probability, threshold)
    if tier == "High":
        return "Critical Passengers"
    if tier in {"Elevated", "Watch"}:
        return "At-Risk Standard Passengers"
    return "Flexible Passengers"


def airline_review_level(probability: float, threshold: float, network_critical: bool) -> str:
    tier = risk_tier(probability, threshold)
    if tier == "High" or (tier == "Elevated" and network_critical):
        return "Early operational review"
    if tier in {"Elevated", "Watch"}:
        return "Monitor and prepare"
    return "Standard monitoring"


def airport_actions(priority: str, network_critical: bool) -> list[str]:
    if priority == "High":
        actions = [
            "Prioritise this flight by delay risk in the departure bank.",
            "Pre-position gates, ramp teams, and staffing for faster recovery.",
            "Use the risk score for passenger-flow planning and queue pressure.",
        ]
        if network_critical:
            actions.append("Monitor this route as network-critical because disruption may spread to later flights.")
        return actions
    if priority == "Medium":
        return [
            "Place the flight on an airport watchlist instead of treating it as routine.",
            "Check gate, ramp, and staffing availability before the delay escalates.",
            "Monitor nearby peak departure banks and connecting passenger flow.",
        ]
    return [
        "Keep standard airport monitoring active.",
        "Do not pull scarce gate, ramp, or staffing resources away from higher-risk flights.",
        "Continue automated passenger-flow monitoring.",
    ]


def airline_actions(review_level: str, focus_segment: str) -> list[str]:
    if review_level == "Early operational review":
        return [
            "Identify the flight for early operational review.",
            "Check crew legality, aircraft rotation, and recovery options.",
            f"Protect {focus_segment.lower()} before disruption escalates.",
            "Prepare rebooking and communication options before the delay is confirmed.",
        ]
    if review_level == "Monitor and prepare":
        return [
            "Monitor the flight for delay escalation.",
            "Check backup aircraft, crew, and connection exposure if resources allow.",
            f"Prepare automated communication for {focus_segment.lower()}.",
        ]
    return [
        "Keep the flight in standard operations monitoring.",
        "Use automated updates unless the risk score increases.",
        "Reserve manual intervention for higher-risk flights.",
    ]


def action_list_html(title: str, actions: list[str], priority: str | None = None) -> str:
    priority_class = {
        "High": "priority-high",
        "Medium": "priority-medium",
        "Normal": "priority-normal",
    }.get(priority or "", "")
    priority_html = f"<p class='{priority_class}'>{priority} priority</p>" if priority else ""
    items = "".join(f"<li>{action}</li>" for action in actions)
    return f"""
    <div class="decision-card">
        <h4>{title}</h4>
        {priority_html}
        <ul>{items}</ul>
    </div>
    """


def airport_display_name(airport_code: str, airports: pd.DataFrame) -> str:
    matches = airports[airports["iata_code"] == airport_code]
    if matches.empty:
        catalog = load_airport_catalog()
        matches = catalog[catalog["iata_code"] == airport_code]
    if matches.empty:
        fallback = AIRPORT_FALLBACK.get(airport_code)
        return fallback[0] if fallback else airport_code
    return str(matches.iloc[0]["name"])


def destination_place_name(airport_code: str, airports: pd.DataFrame) -> str:
    matches = airports[airports["iata_code"] == airport_code]
    if matches.empty:
        catalog = load_airport_catalog()
        matches = catalog[catalog["iata_code"] == airport_code]
    if not matches.empty:
        municipality = str(matches.iloc[0].get("municipality", "") or "").strip()
        if municipality and municipality.lower() != "nan":
            return municipality
    airport_name = airport_display_name(airport_code, airports)
    for suffix in [" International Airport", " Airport", " Intl", " International"]:
        airport_name = airport_name.replace(suffix, "")
    return airport_name.strip() or airport_code


def destination_country_code(airport_code: str, airports: pd.DataFrame) -> str:
    matches = airports[airports["iata_code"] == airport_code]
    if matches.empty:
        catalog = load_airport_catalog()
        matches = catalog[catalog["iata_code"] == airport_code]
    if matches.empty:
        return ""
    value = str(matches.iloc[0].get("iso_country", "") or "").strip().upper()
    return "" if value.lower() == "nan" else value


def markdown_link_text(value: str) -> str:
    return value.replace("[", "(").replace("]", ")").strip()


def short_text(value: str, limit: int = 700) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0] + "..."


def sentence_points(value: str, limit: int = 3) -> list[str]:
    text = " ".join(value.split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 35][:limit]


def fallback_image_url(seed: str) -> str:
    colors = ["0f766e", "2563eb", "f97316", "7c3aed", "be123c"]
    color = colors[sum(ord(char) for char in seed) % len(colors)]
    label = urllib.parse.quote(seed[:28])
    return f"https://placehold.co/900x520/{color}/ffffff?text={label}"


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_commons_image(query: str) -> dict[str, str]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": query,
        "gsrlimit": "1",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "900",
    }
    url = f"{COMMONS_API_URL}?{urllib.parse.urlencode(params)}"
    try:
        payload = request_json(url, timeout=10)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DestinationInfoError("Image search is unavailable right now.") from exc

    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        image_url = str(info.get("thumburl") or info.get("url") or "")
        if image_url:
            return {
                "url": image_url,
                "source": str(info.get("descriptionurl") or ""),
                "title": str(page.get("title") or query).replace("File:", ""),
            }
    raise DestinationInfoError("No related image was found.")


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_wikipedia_summary(place: str) -> dict[str, str]:
    title = urllib.parse.quote(place.replace(" ", "_"), safe="")
    url = WIKIPEDIA_SUMMARY_URL.format(title=title)
    try:
        payload = request_json(url, timeout=10)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DestinationInfoError("Destination overview is unavailable right now.") from exc

    extract = str(payload.get("extract") or "").strip()
    if not extract:
        raise DestinationInfoError("No destination overview was found.")
    return {
        "title": str(payload.get("title") or place),
        "extract": extract,
        "url": str((payload.get("content_urls") or {}).get("desktop", {}).get("page") or ""),
        "image": str((payload.get("thumbnail") or {}).get("source") or ""),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_wikivoyage_tips(place: str) -> dict[str, str]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "extracts|info",
        "exintro": "1",
        "explaintext": "1",
        "inprop": "url",
        "redirects": "1",
        "titles": place,
    }
    url = f"{WIKIVOYAGE_API_URL}?{urllib.parse.urlencode(params)}"
    try:
        payload = request_json(url, timeout=10)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DestinationInfoError("Travel guide tips are unavailable right now.") from exc

    pages = (payload.get("query") or {}).get("pages") or []
    page = pages[0] if pages else {}
    extract = str(page.get("extract") or "").strip()
    if not extract:
        raise DestinationInfoError("No travel guide tips were found.")
    return {
        "title": str(page.get("title") or place),
        "extract": extract,
        "url": str(page.get("fullurl") or ""),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_wikivoyage_section_text(place: str, section_names: tuple[str, ...]) -> str:
    section_params = {
        "action": "parse",
        "format": "json",
        "page": place,
        "prop": "sections",
        "redirects": "1",
    }
    section_url = f"{WIKIVOYAGE_API_URL}?{urllib.parse.urlencode(section_params)}"
    try:
        section_payload = request_json(section_url, timeout=10)
        sections = (section_payload.get("parse") or {}).get("sections") or []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DestinationInfoError("Travel guide section is unavailable right now.") from exc

    wanted = {name.lower() for name in section_names}
    section_index = ""
    for section in sections:
        line = str(section.get("line") or "").strip().lower()
        if line in wanted:
            section_index = str(section.get("index") or "")
            break
    if not section_index:
        raise DestinationInfoError("This destination guide does not have that section.")

    text_params = {
        "action": "parse",
        "format": "json",
        "page": place,
        "prop": "text",
        "section": section_index,
        "redirects": "1",
    }
    text_url = f"{WIKIVOYAGE_API_URL}?{urllib.parse.urlencode(text_params)}"
    try:
        text_payload = request_json(text_url, timeout=10)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DestinationInfoError("Travel guide section is unavailable right now.") from exc

    html_text = str(((text_payload.get("parse") or {}).get("text") or {}).get("*") or "")
    text = strip_html(html_text)
    if not text:
        raise DestinationInfoError("No useful guide text was found.")
    return text


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_google_news_items(query: str, max_items: int = 5) -> list[dict[str, str]]:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    url = f"{GOOGLE_NEWS_RSS_URL}?{urllib.parse.urlencode(params)}"
    try:
        root = ET.fromstring(request_text(url, timeout=10))
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
        raise DestinationInfoError("Live destination updates are unavailable right now.") from exc

    items = []
    for item in root.findall(".//item")[:max_items]:
        title = str(item.findtext("title") or "").strip()
        link = str(item.findtext("link") or "").strip()
        published = str(item.findtext("pubDate") or "").strip()
        source = item.find("source")
        source_name = str(source.text or "").strip() if source is not None else ""
        source_url = str(source.attrib.get("url", "")).strip() if source is not None else ""
        image_url = favicon_url(source_url or link)
        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": source_name,
                    "source_url": source_url,
                    "image": image_url,
                }
            )
    if not items:
        raise DestinationInfoError("No live destination updates were found.")
    return items


def favicon_url(url: str, size: int = 96) -> str:
    return f"https://www.google.com/s2/favicons?domain_url={urllib.parse.quote(url)}&sz={size}"


def fetch_destination_news(place: str) -> list[dict[str, str]]:
    return fetch_google_news_items(f"{place} travel airport tourism", max_items=5)


def fetch_destination_topic_updates(place: str, topic: str, max_items: int = 3) -> list[dict[str, str]]:
    return fetch_google_news_items(f"{place} {topic}", max_items=max_items)


def fetch_social_trend_items(place: str, max_items: int = 4) -> list[dict[str, str]]:
    queries = [
        f"{place} TikTok viral travel food attraction",
        f"{place} Instagram viral travel food attraction",
        f"{place} viral food attraction travel trend",
    ]
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        try:
            for item in fetch_google_news_items(query, max_items=max_items):
                key = item["link"]
                if key not in seen:
                    merged.append(item)
                    seen.add(key)
                if len(merged) >= max_items:
                    return merged
        except DestinationInfoError:
            continue
    if merged:
        return merged
    return [
        {
            "title": f"Open TikTok search for viral {place} travel and food",
            "link": social_search_url("tiktok", place),
            "published": "Live platform search",
            "source": "TikTok",
            "image": favicon_url("https://www.tiktok.com"),
        },
        {
            "title": f"Open Instagram search for trending {place} places",
            "link": social_search_url("instagram", place),
            "published": "Live platform search",
            "source": "Instagram",
            "image": favicon_url("https://www.instagram.com"),
        },
        {
            "title": f"Search web for latest viral {place} activities and food",
            "link": f"https://www.google.com/search?q={urllib.parse.quote_plus(place + ' latest viral travel food activities')}",
            "published": "Live web search",
            "source": "Web search",
            "image": favicon_url("https://www.google.com"),
        },
    ][:max_items]


def social_search_url(platform: str, place: str) -> str:
    query = urllib.parse.quote_plus(f"{place} travel food")
    if platform == "tiktok":
        return f"https://www.tiktok.com/search?q={query}"
    if platform == "instagram":
        return f"https://www.instagram.com/explore/search/keyword/?q={query}"
    return f"https://www.google.com/search?q={query}"


def clean_listing_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" -,:;")
    return name[:90]


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_wikivoyage_listing_names(place: str, section_names: tuple[str, ...], max_items: int = 6) -> list[str]:
    section_params = {
        "action": "parse",
        "format": "json",
        "page": place,
        "prop": "sections",
        "redirects": "1",
    }
    section_url = f"{WIKIVOYAGE_API_URL}?{urllib.parse.urlencode(section_params)}"
    try:
        section_payload = request_json(section_url, timeout=10)
        sections = (section_payload.get("parse") or {}).get("sections") or []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    wanted = {name.lower() for name in section_names}
    names: list[str] = []
    for section in sections:
        line = str(section.get("line") or "").strip().lower()
        if line not in wanted:
            continue
        text_params = {
            "action": "parse",
            "format": "json",
            "page": place,
            "prop": "text",
            "section": str(section.get("index") or ""),
            "redirects": "1",
        }
        text_url = f"{WIKIVOYAGE_API_URL}?{urllib.parse.urlencode(text_params)}"
        try:
            text_payload = request_json(text_url, timeout=10)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        html_text = str(((text_payload.get("parse") or {}).get("text") or {}).get("*") or "")
        parser = ListingNameParser()
        parser.feed(html_text)
        for name in parser.names:
            cleaned = clean_listing_name(name)
            if cleaned and cleaned not in names:
                names.append(cleaned)
            if len(names) >= max_items:
                return names
    return names


def osm_search_url(name: str, place: str) -> str:
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(name + ' ' + place)}"


@st.cache_data(ttl=43200, show_spinner=False)
def fetch_osm_recommendations(
    latitude: float,
    longitude: float,
    place: str,
    kind: str,
    max_items: int = 6,
) -> list[dict[str, str]]:
    if kind == "hotel":
        radius = 30000
        filters = '["tourism"~"hotel|hostel|guest_house|apartment"]'
    else:
        radius = 45000
        filters = '["tourism"~"attraction|museum|viewpoint|theme_park|zoo|aquarium|gallery"]'

    query = f"""
    [out:json][timeout:14];
    (
      node{filters}(around:{radius},{latitude},{longitude});
      way{filters}(around:{radius},{latitude},{longitude});
      relation{filters}(around:{radius},{latitude},{longitude});
    );
    out center tags {max_items * 4};
    """
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(OVERPASS_API_URL, data=data, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for element in payload.get("elements") or []:
        tags = element.get("tags") or {}
        name = clean_listing_name(str(tags.get("name:en") or tags.get("name") or ""))
        if not name or name.lower() in seen:
            continue
        lat_value = element.get("lat") or (element.get("center") or {}).get("lat")
        lon_value = element.get("lon") or (element.get("center") or {}).get("lon")
        seen.add(name.lower())
        category = str(tags.get("tourism") or tags.get("historic") or kind).replace("_", " ").title()
        website = str(tags.get("website") or tags.get("contact:website") or "")
        address_parts = [
            str(tags.get("addr:street") or ""),
            str(tags.get("addr:city") or ""),
        ]
        detail = " | ".join(part for part in [category, ", ".join(part for part in address_parts if part)] if part)
        items.append(
            {
                "name": name,
                "detail": detail or category,
                "url": website or osm_search_url(name, place),
                "booking_url": booking_hotel_url(f"{name} {place}", date.today()) if kind == "hotel" else klook_activity_url(f"{name} {place}"),
                "lat": float(lat_value) if lat_value is not None else None,
                "lon": float(lon_value) if lon_value is not None else None,
            }
        )
        if len(items) >= max_items:
            break
    return items


def wikivoyage_recommendation_items(place: str, section_names: tuple[str, ...], kind: str, max_items: int = 6) -> list[dict[str, str]]:
    names = fetch_wikivoyage_listing_names(place, section_names, max_items=max_items)
    items = []
    for name in names:
        items.append(
            {
                "name": name,
                "detail": "Named in Wikivoyage travel guide",
                "url": osm_search_url(name, place),
                "booking_url": booking_hotel_url(f"{name} {place}", date.today()) if kind == "hotel" else klook_activity_url(f"{name} {place}"),
                "lat": None,
                "lon": None,
            }
        )
    return items


def destination_recommendation_map_rows(
    dest_airport: str,
    dest_name: str,
    latitude: float,
    longitude: float,
    hotel_items: list[dict[str, object]],
    activity_items: list[dict[str, object]],
) -> pd.DataFrame:
    rows = [
        {
            "name": f"{dest_airport} airport area",
            "type": "Destination center",
            "lat": latitude,
            "lon": longitude,
            "text": "DEST",
            "color": [15, 118, 110],
            "radius": 520,
        }
    ]
    for item in hotel_items[:5]:
        if item.get("lat") is None or item.get("lon") is None:
            continue
        rows.append(
            {
                "name": str(item.get("name") or "Hotel"),
                "type": "Hotel",
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "text": "HOTEL",
                "color": [236, 72, 153],
                "radius": 420,
            }
        )
    for item in activity_items[:5]:
        if item.get("lat") is None or item.get("lon") is None:
            continue
        rows.append(
            {
                "name": str(item.get("name") or "Attraction"),
                "type": "Attraction",
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "text": "SEE",
                "color": [249, 115, 22],
                "radius": 450,
            }
        )
    return pd.DataFrame(rows)


def booking_hotel_url(place: str, checkin: date) -> str:
    checkout = checkin + timedelta(days=1)
    params = {
        "ss": place,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "group_adults": "1",
        "no_rooms": "1",
        "group_children": "0",
    }
    return f"https://www.booking.com/searchresults.html?{urllib.parse.urlencode(params)}"


def google_hotel_url(place: str, checkin: date) -> str:
    return f"https://www.google.com/travel/hotels/{urllib.parse.quote(place)}?checkin={checkin.isoformat()}&checkout={(checkin + timedelta(days=1)).isoformat()}&adults=1"


def hotels_com_url(place: str, checkin: date) -> str:
    checkout = checkin + timedelta(days=1)
    params = {
        "destination": place,
        "startDate": checkin.isoformat(),
        "endDate": checkout.isoformat(),
        "rooms": "1",
        "adults": "1",
    }
    return f"https://www.hotels.com/Hotel-Search?{urllib.parse.urlencode(params)}"


def expedia_hotel_url(place: str, checkin: date) -> str:
    checkout = checkin + timedelta(days=1)
    params = {
        "destination": place,
        "startDate": checkin.isoformat(),
        "endDate": checkout.isoformat(),
        "rooms": "1",
        "adults": "1",
    }
    return f"https://www.expedia.com/Hotel-Search?{urllib.parse.urlencode(params)}"


def agoda_hotel_url(place: str, checkin: date) -> str:
    params = {
        "textToSearch": place,
        "checkIn": checkin.isoformat(),
        "los": "1",
        "rooms": "1",
        "adults": "1",
        "children": "0",
    }
    return f"https://www.agoda.com/search?{urllib.parse.urlencode(params)}"


def trip_com_hotel_url(place: str, checkin: date) -> str:
    checkout = checkin + timedelta(days=1)
    params = {
        "city": place,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "adults": "1",
        "rooms": "1",
    }
    return f"https://www.trip.com/hotels/list?{urllib.parse.urlencode(params)}"


def hotel_booking_urls(place: str, checkin: date) -> dict[str, str]:
    return {
        "Booking.com": booking_hotel_url(place, checkin),
        "Google Hotels": google_hotel_url(place, checkin),
        "Hotels.com": hotels_com_url(place, checkin),
        "Expedia": expedia_hotel_url(place, checkin),
        "Agoda": agoda_hotel_url(place, checkin),
        "Trip.com Hotels": trip_com_hotel_url(place, checkin),
    }


def klook_activity_url(place: str) -> str:
    return f"https://www.klook.com/search/result/?query={urllib.parse.quote_plus(place)}"


def flight_search_url(origin: str, dest: str, flight_date: date) -> str:
    query = f"best price flights {origin} to {dest} {flight_date.isoformat()}"
    return f"https://www.google.com/travel/flights?q={urllib.parse.quote_plus(query)}"


def trip_com_flight_url(origin: str, dest: str, flight_date: date) -> str:
    query = urllib.parse.quote_plus(f"{origin} to {dest} {flight_date.isoformat()}")
    return f"https://www.trip.com/flights/index?locale=en_us&search={query}"


def skyscanner_flight_url(origin: str, dest: str, flight_date: date) -> str:
    date_token = flight_date.strftime("%y%m%d")
    return f"https://www.skyscanner.com/transport/flights/{origin.lower()}/{dest.lower()}/{date_token}/?adults=1&adultsv2=1&cabinclass=economy&children=0&inboundaltsenabled=false&outboundaltsenabled=false&rtn=0"


def traveloka_flight_url(origin: str, dest: str, flight_date: date) -> str:
    params = {
        "ap": f"{origin}.{dest}",
        "dt": flight_date.isoformat(),
        "ps": "1.0.0",
        "sc": "ECONOMY",
    }
    return f"https://www.traveloka.com/en-en/flight/fullsearch?{urllib.parse.urlencode(params)}"


def tiket_flight_url(origin: str, dest: str, flight_date: date) -> str:
    params = {
        "d": origin,
        "a": dest,
        "date": flight_date.isoformat(),
        "adult": "1",
        "child": "0",
        "infant": "0",
        "class": "economy",
    }
    return f"https://www.tiket.com/pesawat/search?{urllib.parse.urlencode(params)}"


def flight_booking_urls(origin: str, dest: str, flight_date: date) -> dict[str, str]:
    return {
        "Google Flights": flight_search_url(origin, dest, flight_date),
        "Skyscanner": skyscanner_flight_url(origin, dest, flight_date),
        "Trip.com": trip_com_flight_url(origin, dest, flight_date),
        "Traveloka": traveloka_flight_url(origin, dest, flight_date),
        "Tiket.com": tiket_flight_url(origin, dest, flight_date),
    }


def airline_candidates_for_route(origin: str, dest: str, estimated_code: str) -> list[str]:
    candidates = [estimated_code]
    for airport in (origin, dest):
        if airport in PRIMARY_AIRLINE_BY_AIRPORT:
            candidates.append(PRIMARY_AIRLINE_BY_AIRPORT[airport][0])
    candidates.extend(["AA", "DL", "UA", "WN"])
    seen = []
    for code in candidates:
        if code and code not in seen:
            seen.append(code)
    return seen[:4]


def minutes_from_hhmm(value: str) -> int | None:
    match = re.search(r"(\d{1,2}):(\d{2})", value or "")
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


@st.cache_data(ttl=900, show_spinner=False)
def fetch_route_flight_recommendations(
    origin: str,
    dest: str,
    flight_date: date,
    departure_time: time,
) -> list[dict[str, object]]:
    if not AVIATIONSTACK_API_KEY:
        return []

    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "dep_iata": origin,
        "arr_iata": dest,
        "flight_date": flight_date.isoformat(),
        "limit": "30",
    }
    url = f"{AVIATIONSTACK_FLIGHTS_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    if payload.get("error"):
        return []

    target_minutes = departure_time.hour * 60 + departure_time.minute
    options = []
    for flight in payload.get("data") or []:
        details = flight_details_from_payload(flight, "Aviationstack route lookup")
        if details.get("origin", "").upper() != origin.upper() or details.get("dest", "").upper() != dest.upper():
            continue
        depart_minutes = minutes_from_hhmm(details.get("departure_time", ""))
        if not details.get("flight_number") or depart_minutes is None:
            continue
        airline_code = details.get("airline") or ""
        options.append(
            {
                "label": "Live route match",
                "airline_code": airline_code,
                "airline": airline_name_from_code(airline_code) if airline_code else "Airline shown on booking site",
                "flight_number": details["flight_number"],
                "is_live": True,
                "time": details.get("departure_time", ""),
                "arrival_time": details.get("arrival_time") or "Check booking site",
                "detail": f"Route result from Aviationstack. Status: {details.get('status') or 'check live booking site'}.",
                "url": flight_search_url(origin, dest, flight_date),
                "booking_urls": flight_booking_urls(origin, dest, flight_date),
                "sort_delta": abs(depart_minutes - target_minutes),
            }
        )

    labels = ["Closest live match", "Another live option", "More live choice"]
    ranked = sorted(options, key=lambda item: int(item["sort_delta"]))[:3]
    for label, option in zip(labels, ranked):
        option["label"] = label
        option.pop("sort_delta", None)
    return ranked


def route_search_recommendations(
    origin: str,
    dest: str,
    flight_date: date,
) -> list[dict[str, object]]:
    return [
        {
            "label": "Best price search",
            "title": "Compare lowest fares",
            "route": f"{origin}-{dest}",
            "detail": "Demo route-search example, not a live flight. Opens booking sites so users can compare real flight numbers, times, and fares.",
            "booking_urls": flight_booking_urls(origin, dest, flight_date),
        },
        {
            "label": "Fewest stops search",
            "title": "Look for direct or shortest trips",
            "route": f"{origin}-{dest}",
            "detail": "Demo route-search example, not a live flight. Use filters on booking sites for non-stop flights or shorter total duration.",
            "booking_urls": flight_booking_urls(origin, dest, flight_date),
        },
        {
            "label": "Flexible timing search",
            "title": "Check nearby times",
            "route": f"{origin}-{dest}",
            "detail": "Demo route-search example, not a live flight. Compare morning, afternoon, and evening departures on the booking sites.",
            "booking_urls": flight_booking_urls(origin, dest, flight_date),
        },
    ]


def top_airlines_for_route(origin: str, dest: str, selected_code: str, airline_choice: str) -> list[dict[str, str]]:
    candidates: list[tuple[str, str]] = []
    if airline_choice != AIRLINE_AUTO_LABEL and selected_code:
        candidates.append((selected_code, "Selected by the user as a preferred airline filter."))
    if origin in PRIMARY_AIRLINE_BY_AIRPORT:
        code, reason = PRIMARY_AIRLINE_BY_AIRPORT[origin]
        candidates.append((code, f"Strong presence at the departure airport. {reason}"))
    if dest in PRIMARY_AIRLINE_BY_AIRPORT:
        code, reason = PRIMARY_AIRLINE_BY_AIRPORT[dest]
        candidates.append((code, f"Strong presence at the destination airport. {reason}"))
    for code, reason in [
        ("DL", "Large network carrier to compare when route-specific data is unavailable."),
        ("AA", "Large network carrier to compare when route-specific data is unavailable."),
        ("UA", "Large network carrier to compare when route-specific data is unavailable."),
    ]:
        candidates.append((code, reason))

    seen: set[str] = set()
    airlines = []
    for code, reason in candidates:
        if not code or code in seen:
            continue
        seen.add(code)
        airlines.append({"code": code, "name": airline_name_from_code(code), "reason": reason})
        if len(airlines) >= 3:
            break
    return airlines


def render_news_card(item: dict[str, str]) -> None:
    title = escape(markdown_link_text(item.get("title", "Open story")))
    image = escape(item.get("image") or favicon_url(item.get("link", "")))
    source = escape(item.get("source") or "News source")
    published = escape(item.get("published", ""))
    link = escape(item.get("link", "#"))
    st.markdown(
        f"""
        <div class="feed-card">
            <img src="{image}" alt="{source}">
            <div>
                <div class="feed-title"><a href="{link}" target="_blank">{title}</a></div>
                <div class="feed-meta">{source}<br>{published}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_simple_card(title: str, bullets: list[str]) -> None:
    st.markdown(f"##### {title}")
    st.markdown("\n".join(f"- {bullet}" for bullet in bullets))


def weather_icon_class(weather_name: str) -> str:
    return {
        "Clear": "icon-clear",
        "Cloudy": "icon-cloudy",
        "Rain": "icon-rain",
        "Storm": "icon-storm",
        "Snow": "icon-snow",
        "Fog": "icon-fog",
        "Windy": "icon-windy",
    }.get(weather_name, "icon-cloudy")


def weather_icon_html(weather_name: str) -> str:
    icon = {
        "Clear": "&#9728;",
        "Cloudy": "&#9729;",
        "Rain": "&#9748;",
        "Storm": "&#9889;",
        "Snow": "&#10052;",
        "Fog": "&#9776;",
        "Windy": "&#8767;",
    }.get(weather_name, "&#9729;")
    return f'<span class="auto-icon {weather_icon_class(weather_name)}">{icon}</span>'


def crowd_icon_html(traffic_name: str) -> str:
    if traffic_name in {"Busy", "Very busy"}:
        return '<span class="auto-icon icon-crowd">&#128101;</span>'
    return '<span class="auto-icon icon-quiet">&#128100;</span>'


def auto_icon(icon_class: str, icon_html: str) -> str:
    return f'<span class="auto-icon {icon_class}">{icon_html}</span>'


def estimated_fare_text(distance_miles: float, flight_date: date, option_index: int = 0, currency: str = "USD") -> str:
    if distance_miles < 500:
        base = 85
    elif distance_miles < 1500:
        base = 155
    elif distance_miles < 3500:
        base = 310
    else:
        base = 575
    if holiday_flags(flight_date)["IS_PEAK_TRAVEL"]:
        base *= 1.18
    multipliers = [1.0, 1.08, 0.94, 1.15]
    usd_amount = base * multipliers[option_index % len(multipliers)]
    rate = CURRENCY_RATES.get(currency, 1.0)
    converted = usd_amount * rate
    if currency in {"IDR", "JPY"}:
        amount = int(round(converted / 1000) * 1000) if currency == "IDR" else int(round(converted / 100) * 100)
    else:
        amount = int(round(converted / 10) * 10)
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return f"Est. from {symbol}{amount:,.0f}"


def local_transportation_tips(place: str, country_code: str, airport_code: str) -> list[str]:
    tips = [
        f"Check whether {airport_code} has an airport train, metro, express bus, or official shuttle before you land.",
        "For the first ride from the airport, use official taxi stands, airport transfer desks, or trusted ride-hailing apps.",
        "If you will explore the city for several days, compare a transit day pass with single tickets before buying.",
        "Save your hotel address in the local language and keep an offline map in case mobile data is slow on arrival.",
        "Avoid booking a tightly timed tour right after landing; leave room for immigration, baggage, traffic, and delays.",
    ]
    if country_code in {"JP", "SG", "HK", "KR", "NL", "GB", "FR", "DE"}:
        tips.insert(1, "Public transport is usually a strong first choice in this destination; look for stored-value cards or airport rail links.")
    elif country_code in {"US", "CA", "AU"}:
        tips.insert(1, "Rideshare, taxi, or rental car may be more convenient outside dense city centers; compare parking and traffic before choosing.")
    return tips[:5]


def culinary_recommendations(place: str, guide_text: str) -> list[str]:
    points = sentence_points(guide_text, 3)
    if points:
        return points[:3]
    return [
        f"Try a well-rated local restaurant or food market in {place}.",
        "Ask hotel staff or locals for one dish that visitors should not miss.",
        "Check opening hours before you travel from the airport, especially after a late arrival.",
    ]


def souvenir_recommendations(place: str, guide_text: str) -> list[str]:
    points = sentence_points(guide_text, 3)
    if points:
        return points[:3]
    return [
        f"Look for locally made gifts, snacks, or crafts from {place}.",
        "Choose small items that pack safely in cabin or checked luggage.",
        "Keep receipts for higher-value purchases in case customs asks for them.",
    ]


def destination_fun_facts(place: str, overview_text: str, dest_airport: str, airport_name: str, distance_miles: float) -> list[str]:
    facts = sentence_points(overview_text, 2)
    facts.append(f"Your destination airport is {dest_airport}, {airport_name}.")
    facts.append(f"This route covers about {distance_miles:,.0f} miles.")
    return facts[:4]


def passenger_risk_name(probability: float, threshold: float) -> str:
    if probability >= max(0.45, threshold + 0.2):
        return "Very High"
    if probability >= threshold:
        return "High"
    if probability >= max(0.12, threshold * 0.65):
        return "Moderate"
    return "Low"


def weather_passenger_message(weather_name: str, weather: dict[str, float]) -> str:
    if weather_name in {"Storm", "Snow"}:
        return "Weather may slow ground operations, boarding, or departure sequencing."
    if weather_name in {"Rain", "Windy", "Fog"}:
        return "Weather could add some airport handling or departure pressure."
    if weather["wind_gusts_10m"] >= 45:
        return "Wind gusts are elevated, so keep an eye on airport updates."
    return "Weather looks manageable for passengers, but flight status can still change."


def passenger_reasons(
    probability: float,
    threshold: float,
    weather_name: str,
    weather: dict[str, float],
    traffic_name: str,
    recent_delay_name: str,
    departure_time: time,
    network_critical: bool,
    flight_date: date,
) -> list[str]:
    reasons = []
    if traffic_name in {"Busy", "Very busy"}:
        reasons.append(f"{departure_time:%H:%M} is estimated as a {traffic_name.lower()} airport period.")
    if weather_name in {"Rain", "Storm", "Snow", "Fog", "Windy"}:
        reasons.append(f"Departure weather is {weather_name.lower()}, with {weather['wind_speed_10m']:.0f} km/h wind.")
    if recent_delay_name in {"Some", "Many"}:
        reasons.append(f"Recent delay pressure is estimated as {recent_delay_name.lower()}.")
    if network_critical:
        reasons.append("This route or departure time may be sensitive to network disruption.")
    if holiday_flags(flight_date)["IS_NEAR_HOLIDAY"]:
        reasons.append("The date is close to a busy travel period.")

    if not reasons:
        reasons.append("No major weather, timing, or airport-pressure warning stands out.")
    if probability >= threshold and len(reasons) < 3:
        reasons.append("The model still finds enough combined pressure to recommend closer monitoring.")
    return reasons[:3]


def recommended_airport_arrival_minutes(
    probability: float,
    threshold: float,
    traffic_name: str,
    checked_bags: bool,
    needs_extra_time: bool,
) -> int:
    minutes = 120
    if probability >= max(0.45, threshold + 0.2):
        minutes += 45
    elif probability >= threshold:
        minutes += 30
    elif probability >= max(0.12, threshold * 0.65):
        minutes += 15
    if traffic_name == "Very busy":
        minutes += 30
    elif traffic_name == "Busy":
        minutes += 15
    if checked_bags:
        minutes += 20
    if needs_extra_time:
        minutes += 20
    return minutes


def airport_arrival_text(flight_date: date, departure_time: time, minutes_before: int) -> str:
    departure_dt = datetime.combine(flight_date, departure_time)
    arrival_dt = departure_dt - timedelta(minutes=minutes_before)
    return f"{arrival_dt:%H:%M} ({minutes_before // 60}h {minutes_before % 60:02d}m before departure)"


def leave_home_text(flight_date: date, departure_time: time, minutes_before: int, travel_minutes: int) -> str:
    departure_dt = datetime.combine(flight_date, departure_time)
    leave_dt = departure_dt - timedelta(minutes=minutes_before + travel_minutes)
    return f"{leave_dt:%H:%M}"


def estimate_destination_arrival_text(
    flight_date: date,
    departure_time: time,
    distance_miles: float,
    lookup_details: dict[str, str],
) -> tuple[str, str]:
    if lookup_details.get("arrival_time"):
        return lookup_details["arrival_time"], "Scheduled arrival from flight lookup."

    duration_minutes = int(max(45, min(720, (distance_miles / 500.0) * 60 + 35)))
    arrival_dt = datetime.combine(flight_date, departure_time) + timedelta(minutes=duration_minutes)
    return arrival_dt.strftime("%H:%M"), f"Estimated from route distance, about {duration_minutes // 60}h {duration_minutes % 60:02d}m flight time."


def hour_from_time_text(value: str, fallback: int) -> int:
    match = re.search(r"(\d{1,2}):(\d{2})", value)
    if not match:
        return fallback
    return max(0, min(23, int(match.group(1))))


def connection_risk(
    has_connection: bool,
    connection_minutes: int,
    probability: float,
    threshold: float,
) -> tuple[str, str]:
    if not has_connection:
        return "Not applicable", "No connection entered."
    if connection_minutes < 45:
        return "Very High", "This is a tight connection even without a delay."
    if probability >= threshold and connection_minutes < 90:
        return "High", "A moderate delay could put this connection at risk."
    if probability >= max(0.12, threshold * 0.65) and connection_minutes < 75:
        return "Moderate", "Keep the airline app open and review backup options."
    return "Low", "Your connection buffer looks reasonable for this risk level."


def passenger_action_plan(
    passenger_risk: str,
    arrival_text: str,
    leave_text: str,
    connection_label: str,
    has_connection: bool,
) -> list[str]:
    actions = [f"Leave for the airport by {leave_text} and be at the airport by {arrival_text}."]
    if passenger_risk in {"High", "Very High"}:
        actions.append("Turn on airline notifications and check the flight again before you leave.")
        actions.append("Do not plan a tight airport arrival.")
    elif passenger_risk == "Moderate":
        actions.append("Keep notifications on and check the flight before leaving home.")
    else:
        actions.append("Normal timing should be okay, but keep airline notifications on.")
    if has_connection and connection_label in {"High", "Very High"}:
        actions.append("Because your connection may be tight, check backup options in the airline app.")
    return actions


def airport_map_rows(origin: str, dest: str, airports: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for code, label, color in [(origin, "Takeoff", [20, 184, 166]), (dest, "Landing", [249, 115, 22])]:
        lat, lon = airport_location(code, airports)
        rows.append(
            {
                "code": code,
                "label": label,
                "lat": lat,
                "lon": lon,
                "name": airport_display_name(code, airports),
                "color": color,
                "text": f"{label}\n{code}",
            }
        )
    points = pd.DataFrame(rows)
    line = pd.DataFrame(
        [
            {
                "from": origin,
                "to": dest,
                "source": [float(points.iloc[0]["lon"]), float(points.iloc[0]["lat"])],
                "target": [float(points.iloc[1]["lon"]), float(points.iloc[1]["lat"])],
                "color": [37, 99, 235],
            }
        ]
    )
    return points, line


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


if not rebuild_split_model_artifact(MODEL_PATH):
    st.error(
        f"Model artifact not found: {MODEL_PATH}. "
        f"Upload {MODEL_PATH.name}.part-001 and {MODEL_PATH.name}.part-002 to {MODEL_PATH.parent}."
    )
    st.stop()

artifact = load_artifact()
metadata = load_metadata()
airports = load_airports()
airport_labels = airport_label_map(airports)
airport_options = list(airport_labels)
airport_count = len(airport_options)
airline_count = len(AIRLINES)
default_threshold = float(artifact.get("threshold", metadata.get("best_threshold", 0.21)))
mode_settings = threshold_modes(default_threshold)

control_cols = st.columns([1, 1, 3], gap="small")
with control_cols[0]:
    selected_language = st.selectbox("Language", list(LANGUAGE_COPY), index=0)
with control_cols[1]:
    selected_currency = st.selectbox("Currency", list(CURRENCY_RATES), index=0)
ui_copy = LANGUAGE_COPY[selected_language]
st.session_state.page_language = selected_language

st.markdown(
    f"""
    <section class="hero-banner">
        <div class="hero-eyebrow">{escape(ui_copy["eyebrow"])}</div>
        <div class="hero-title">{escape(ui_copy["title"])}</div>
        <div class="hero-subtitle">
            {escape(ui_copy["subtitle"])}
        </div>
        <span class="hero-pill">Weather-aware</span>
        <span class="hero-pill">Passenger-friendly</span>
        <span class="hero-pill">Travel tips included</span>
    </section>
    """,
    unsafe_allow_html=True,
)
install_page_translation(selected_language)

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("## Find Flight")
    input_mode = st.radio(
        "Input method",
        ["Route and time", "Flight lookup"],
        horizontal=True,
    )

    with st.form("flight_form"):
        lookup_identifier = ""
        lookup_date = date.today()
        lookup_details: dict[str, str] = {}
        origin_index = list(airport_labels.values()).index("JFK") if "JFK" in airport_labels.values() else 0
        dest_index = list(airport_labels.values()).index("LAX") if "LAX" in airport_labels.values() else min(1, len(airport_options) - 1)

        if input_mode == "Route and time":
            route_cols = st.columns(2)
            origin_label = route_cols[0].selectbox("From", airport_options, index=origin_index)
            dest_label = route_cols[1].selectbox("To", airport_options, index=dest_index)
            st.caption(f"{airport_count} origin and destination airports available.")

            schedule_cols = st.columns(2)
            selected_date = schedule_cols[0].date_input(
                "Flight date",
                value=date.today(),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=15),
            )
            selected_time = schedule_cols[1].time_input("Departure time", value=time(17, 30))

            airline_choice = st.selectbox(
                "Airline, if known",
                [AIRLINE_AUTO_LABEL] + list(AIRLINES),
                index=0,
            )
            st.caption(f"{airline_count} airlines available. If yours is not listed, leave Auto estimate selected.")
            origin = airport_labels[origin_label]
            dest = airport_labels[dest_label]
        else:
            lookup_identifier = st.text_input(
                "Flight number or tail number",
                placeholder="Example: AA100, JL740, or N123AA",
            ).strip().upper()
            lookup_date = st.date_input(
                "Date shown in prediction",
                value=date.today(),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=15),
            )
            selected_date = lookup_date
            selected_time = time(12, 0)
            origin = "JFK"
            dest = "LAX"
            airline_choice = AIRLINE_AUTO_LABEL

        st.subheader("Your Trip")
        trip_cols = st.columns(2)
        checked_bags = trip_cols[0].checkbox("I have checked bags")
        needs_extra_time = trip_cols[1].checkbox("I may need extra time")
        travel_minutes = st.number_input(
            "Travel time to airport in minutes",
            min_value=0,
            max_value=240,
            value=45,
            step=5,
        )
        has_connection = st.checkbox("I have a connecting flight")
        connection_minutes = 60
        if has_connection:
            connection_minutes = st.number_input(
                "Connection time in minutes",
                min_value=15,
                max_value=360,
                value=60,
                step=5,
            )

        submit_label = ui_copy["check"] if input_mode == "Route and time" else ui_copy["lookup"]
        submitted = st.form_submit_button(submit_label, type="primary")

        with st.expander("Advanced prediction setting"):
            threshold_mode = st.radio(
                "Threshold mode",
                THRESHOLD_MODE_ORDER,
                index=THRESHOLD_MODE_ORDER.index("Balanced"),
                horizontal=True,
            )
            active_mode = mode_settings[threshold_mode]
            active_threshold = float(active_mode["threshold"])
            st.caption(
                f"{active_mode['description']} "
                f"Validation precision: {percent_text(active_mode['precision'])}; "
                f"recall: {percent_text(active_mode['recall'])}."
            )

    with st.expander("Test examples"):
        st.write("Flight numbers: AA100, DL123, UA200, JL740, VA726, JQ401, S75309, VA500, UA7411, S75227")
        st.write("Tail numbers: N189DN, JA835J")
        st.caption("Flight numbers are more reliable. Tail-number lookup is best-effort because live aircraft registration data is often missing.")

if input_mode == "Flight lookup" and submitted:
    try:
        lookup_details = fetch_flight_by_identifier(lookup_identifier)
        if lookup_details.get("origin"):
            origin = lookup_details["origin"].upper()
        if lookup_details.get("dest"):
            dest = lookup_details["dest"].upper()
        if lookup_details.get("departure_time"):
            hour, minute = lookup_details["departure_time"].split(":")[:2]
            selected_time = time(int(hour), int(minute))
    except FlightLookupError as exc:
        lookup_details = {}
        with left:
            st.error(f"Flight lookup is unavailable: {exc}")

lookup_airline = lookup_details.get("airline", "") if input_mode == "Flight lookup" else ""
airline_code, airline_source_label = resolve_airline(airline_choice, origin, dest, lookup_airline)
airline_label = airline_name_from_code(airline_code)

if selected_date < date.today():
    with right:
        st.warning("Please choose today or a future flight date. This passenger prediction demo does not score past flights.")
    st.stop()
if selected_date > date.today() + timedelta(days=15):
    with right:
        st.warning("Please choose a flight date within the next 15 days. Weather prediction is only supported for this forecast window.")
    st.stop()

manual_weather_name = "Cloudy"
weather_error = ""
weather_details: dict[str, object] | None = None
try:
    latitude, longitude = airport_location(origin, airports)
    weather_details = fetch_open_meteo_weather(origin, latitude, longitude, selected_date, int(selected_time.hour))
    weather_values = weather_details["values"]
    weather_name = str(weather_details["condition"])
    weather_source_label = f"{weather_details['source']} at {weather_details['timestamp']}"
except WeatherFetchError as exc:
    weather_error = str(exc)
    weather_values = WEATHER_PRESETS[manual_weather_name]
    weather_name = manual_weather_name
    weather_source_label = f"Automatic fallback: {manual_weather_name}"

context = estimate_operational_context(origin, dest, selected_date, selected_time, weather_values)
traffic_name = str(context["traffic_name"])
recent_delay_name = str(context["recent_delay_name"])

with left:
    if input_mode == "Flight lookup":
        if lookup_details:
            tail_note = f" | tail {lookup_details['tail_number']}" if lookup_details.get("tail_number") else ""
            st.success(
                f"Loaded {lookup_details.get('flight_number') or lookup_identifier}: "
                f"{origin} to {dest}, {selected_time:%H:%M}, {airline_label}{tail_note}."
            )
        elif not AVIATIONSTACK_API_KEY:
            st.info("Flight lookup is optional. Set AVIATIONSTACK_API_KEY to enable Aviationstack lookup.")
        st.caption("Flight-number lookup is direct. Tail-number lookup is best-effort because Aviationstack often omits aircraft registration data.")
    if weather_error:
        st.warning(f"Weather API fallback used. {weather_error}")

if input_mode == "Flight lookup" and not lookup_details:
    with right:
        st.subheader("Delay Probability")
        st.info("Enter a flight number or tail number to load the route, departure time, airline, weather, and context automatically.")
    st.stop()

feature_row = build_feature_row(
    selected_date,
    selected_time,
    airline_code,
    origin,
    dest,
    weather_values,
    traffic_name,
    recent_delay_name,
    airports,
)

if origin == dest:
    right.warning("Choose different origin and destination airports.")
elif submitted or "last_probability" not in st.session_state:
    scored = score_frame(artifact, feature_row, active_threshold)
    st.session_state.last_probability = float(scored["delay_probability"].iloc[0])
    st.session_state.last_prediction = int(scored["predicted_delay"].iloc[0])
    st.session_state.last_row = feature_row

probability = float(st.session_state.get("last_probability", 0.0))
label = risk_label(probability, active_threshold)
classification = "Delay likely" if probability >= active_threshold else "Delay not likely"
network_critical = is_network_critical(origin, dest, int(selected_time.hour), traffic_name)
priority = airport_priority(probability, active_threshold, network_critical)
focus_segment = passenger_focus(probability, active_threshold)
review_level = airline_review_level(probability, active_threshold, network_critical)
passenger_risk = passenger_risk_name(probability, active_threshold)
arrival_minutes = recommended_airport_arrival_minutes(
    probability,
    active_threshold,
    traffic_name,
    bool(checked_bags),
    bool(needs_extra_time),
)
arrival_text = airport_arrival_text(selected_date, selected_time, arrival_minutes)
leave_text = leave_home_text(selected_date, selected_time, arrival_minutes, int(travel_minutes))
distance_miles = float(feature_row["Distance"].iloc[0])
destination_arrival_text, destination_arrival_source = estimate_destination_arrival_text(
    selected_date,
    selected_time,
    distance_miles,
    lookup_details,
)
destination_place = destination_place_name(dest, airports)
destination_country = destination_country_code(dest, airports)
destination_weather_error = ""
dest_latitude, dest_longitude = airport_location(dest, airports)
try:
    destination_weather_details = fetch_open_meteo_weather(
        dest,
        dest_latitude,
        dest_longitude,
        selected_date,
        hour_from_time_text(destination_arrival_text, int(selected_time.hour)),
    )
    destination_weather_values = destination_weather_details["values"]
    destination_weather_name = str(destination_weather_details["condition"])
    destination_weather_source_label = f"{destination_weather_details['source']} at {destination_weather_details['timestamp']}"
except WeatherFetchError as exc:
    destination_weather_error = str(exc)
    destination_weather_values = WEATHER_PRESETS[manual_weather_name]
    destination_weather_name = manual_weather_name
    destination_weather_source_label = f"Automatic fallback: {manual_weather_name}"
connection_label, connection_message = connection_risk(
    bool(has_connection),
    int(connection_minutes),
    probability,
    active_threshold,
)
reason_list = passenger_reasons(
    probability,
    active_threshold,
    weather_name,
    weather_values,
    traffic_name,
    recent_delay_name,
    selected_time,
    network_critical,
    selected_date,
)
action_plan = passenger_action_plan(passenger_risk, arrival_text, leave_text, connection_label, bool(has_connection))
weather_message = weather_passenger_message(weather_name, weather_values)
current_weather_icon = weather_icon_html(weather_name)
crowd_icon = crowd_icon_html(traffic_name)
destination_weather_message = weather_passenger_message(destination_weather_name, destination_weather_values)
destination_weather_icon = weather_icon_html(destination_weather_name)
recommended_flights = route_search_recommendations(origin, dest, selected_date)
top_airline_filters = top_airlines_for_route(origin, dest, airline_code, airline_choice)
flight_recommendation_source = "Demo route-search examples. These are not live flights, flight numbers, or confirmed airline availability."

with right:
    st.markdown("## Delay Percentage")
    st.subheader("Your Delay Risk")
    st.markdown(
        f"""
        <div class="risk-card">
            <div class="risk-percent">{probability:.0%}</div>
            <span class="risk-label">{passenger_risk} risk</span>
            <div class="action-box">{action_plan[0]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(1.0, probability))

    result_top_cols = st.columns(2)
    result_top_cols[0].metric("Delay chance", f"{probability:.0%}")
    result_top_cols[1].metric("Land around", destination_arrival_text)
    result_bottom_cols = st.columns(2)
    result_bottom_cols[0].metric("Leave by", leave_text)
    result_bottom_cols[1].metric("Be at airport by", arrival_text.split(" ")[0])
    st.caption(f"{origin} to {dest} | {selected_date:%b %d, %Y} at {selected_time:%H:%M}")

st.markdown("## Book Flight & Auto Information")
st.subheader("Flight Booking Comparison")
st.caption(f"{flight_recommendation_source} Booking sites show the final live flight numbers, times, price, availability, baggage rules, and refund policy.")
flight_cols = st.columns(3, gap="large")
for option_index, (flight_col, option) in enumerate(zip(flight_cols, recommended_flights)):
    with flight_col:
        price_text = estimated_fare_text(distance_miles, selected_date, option_index, selected_currency)
        st.markdown(
            f"""
            <div class="flight-card">
                <div class="tag">{escape(str(option.get('label', 'Route search')))}</div>
                <div class="detail">Demo example, not a live flight</div>
                <div class="flight-number">{escape(str(option.get('route', f'{origin}-{dest}')))}</div>
                <div class="airline">{escape(str(option.get('title', 'Compare booking sites')))}</div>
                <div class="price">{price_text}</div>
                <div class="detail">{origin} to {dest}<br>{escape(str(option.get('detail', 'Compare on the booking site.')))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown('<div class="booking-note">Prices on cards are estimates. Compare these sites for live fares, baggage rules, cancellation policy, and payment options.</div>', unsafe_allow_html=True)
first_booking_urls = recommended_flights[0].get("booking_urls") if recommended_flights else {}
booking_urls = first_booking_urls if isinstance(first_booking_urls, dict) else flight_booking_urls(origin, dest, selected_date)
provider_cols = st.columns(len(booking_urls))
provider_notes = {
    "Google Flights": "broad comparison",
    "Skyscanner": "price scanner",
    "Trip.com": "global OTA",
    "Traveloka": "SEA-friendly",
    "Tiket.com": "Indonesia-friendly",
}
for provider_col, (provider, url) in zip(provider_cols, booking_urls.items()):
    with provider_col:
        st.link_button(provider, url)
        st.caption(provider_notes[provider])

st.subheader("Top 3 Airline Filters For This Route")
st.caption("Demo airline suggestions only. These are search filters based on known airport presence and broad networks, not confirmed operating flights or live availability.")
airline_filter_cols = st.columns(3, gap="large")
for index, (airline_col, airline) in enumerate(zip(airline_filter_cols, top_airline_filters), start=1):
    with airline_col:
        st.markdown(
            f"""
            <div class="airline-chip">
                <div class="rank">Filter {index}</div>
                <div class="name">{escape(airline['name'])} ({escape(airline['code'])})</div>
                <div class="reason">{escape(airline['reason'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    '<a class="scroll-cue" href="#your-travel-plan"><span class="cue-kicker">Next step</span><strong>Open Your Travel Plan</strong><small>Checklist, map, destination tips, hotels, and activities are ready below.</small></a>',
    unsafe_allow_html=True,
)

st.subheader("Automatically Loaded Information")
info_cols = st.columns(5)
info_cols[0].markdown(
    f"""
    <div class="context-card">
        <div class="label">{current_weather_icon}<span>Weather</span></div>
        <div class="value">{weather_name}</div>
        <div class="detail">
            &bull; Around {weather_values['temperature_2m']:.1f} C at departure<br>
            &bull; {weather_values['precipitation']:.1f} mm rain/snow expected<br>
            &bull; {weather_message}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
info_cols[1].markdown(
    f"""
    <div class="context-card">
        <div class="label">{crowd_icon}<span>Airport crowd</span></div>
        <div class="value">{traffic_name}</div>
        <div class="detail">
            &bull; Based on airport size and time of day<br>
            &bull; Busy airports may mean longer queues<br>
            &bull; Arrive earlier if you check bags
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
info_cols[2].markdown(
    f"""
    <div class="context-card">
        <div class="label">{auto_icon("icon-delay", "&#9888;")}<span>Delay pressure</span></div>
        <div class="value">{recent_delay_name}</div>
        <div class="detail">
            &bull; Looks at weather, airport crowding, and date<br>
            &bull; Higher pressure means plans can change faster<br>
            &bull; Keep airline alerts turned on
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
info_cols[3].markdown(
    f"""
    <div class="context-card">
        <div class="label">{auto_icon("icon-airline", "&#9992;")}<span>Airline</span></div>
        <div class="value">{airline_label}</div>
        <div class="detail">
            &bull; {airline_source_label}<br>
            &bull; Route: {origin} to {dest}<br>
            &bull; Check the airline app before you leave
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
info_cols[4].markdown(
    f"""
    <div class="context-card">
        <div class="label">{destination_weather_icon}<span>Arrival weather</span></div>
        <div class="value">{destination_weather_name}</div>
        <div class="detail">
            &bull; Expected around landing at {dest}<br>
            &bull; Around {destination_weather_values['temperature_2m']:.1f} C<br>
            &bull; {destination_weather_message}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

summary = pd.DataFrame(
    [
        {"Item": "Airline", "Value": f"{airline_label} ({airline_code})"},
        {"Item": "Airline source", "Value": airline_source_label},
        {"Item": "Departure", "Value": f"{selected_date:%b %d, %Y} at {selected_time:%H:%M}"},
        {"Item": "Route", "Value": f"{origin} to {dest}"},
        {"Item": "Distance", "Value": f"{float(feature_row['Distance'].iloc[0]):,.0f} mi"},
        {"Item": "Checked bags", "Value": "Yes" if checked_bags else "No"},
        {"Item": "Extra time needed", "Value": "Yes" if needs_extra_time else "No"},
        {"Item": "Travel time to airport", "Value": f"{int(travel_minutes)} minutes"},
        {"Item": "Leave for airport by", "Value": leave_text},
        {"Item": "Connection", "Value": f"{connection_label} - {connection_message}"},
        {"Item": "Recommended airport arrival", "Value": arrival_text},
        {"Item": "Destination arrival", "Value": f"{destination_arrival_text} - {destination_arrival_source}"},
        {"Item": "Threshold mode", "Value": threshold_mode},
        {"Item": "Network-critical", "Value": "Yes" if network_critical else "No"},
            {"Item": "Flight lookup", "Value": lookup_details.get("source", "Not used")},
            {"Item": "Flight recommendations", "Value": flight_recommendation_source},
        {"Item": "Weather", "Value": weather_name},
        {"Item": "Weather source", "Value": weather_source_label},
        {"Item": "Destination arrival weather", "Value": f"{destination_weather_name} - {destination_weather_source_label}"},
        {
            "Item": "Weather inputs",
            "Value": (
                f"{weather_values['temperature_2m']:.1f} C, "
                f"{weather_values['precipitation']:.1f} mm precip, "
                f"{weather_values['wind_speed_10m']:.0f} km/h wind"
            ),
        },
        {"Item": "Airport traffic", "Value": f"{traffic_name} - {context['traffic_source']}"},
        {"Item": "Recent delays", "Value": f"{recent_delay_name} - {context['recent_delay_source']}"},
    ]
)
st.markdown('<span id="your-travel-plan"></span>', unsafe_allow_html=True)
st.subheader("Your Travel Plan")
plan_tab, connection_tab, map_tab, destination_tab, travel_news_tab, booking_tab, airline_tab, details_tab = st.tabs(
    ["Plan", "Connection", "Map", "Travel Tips", "Travel News", "Hotels & Activities", "Airline Info", "Details"]
)

with plan_tab:
    plan_cols = st.columns([1, 1], gap="large")
    with plan_cols[0]:
        st.markdown("#### What To Do Now")
        st.markdown("\n".join(f"- {action}" for action in action_plan))
    with plan_cols[1]:
        st.markdown("#### Why This Risk Level")
        st.markdown("\n".join(f"- {reason}" for reason in reason_list))
    st.info(f"Weather at {origin}: {weather_name}. {weather_message}")
    st.success(f"Expected arrival at {dest}: {destination_arrival_text}. {destination_arrival_source}")

with connection_tab:
    conn_cols = st.columns(3)
    conn_cols[0].metric("Connection risk", connection_label)
    conn_cols[1].metric("Connection buffer", f"{int(connection_minutes)} min" if has_connection else "None")
    conn_cols[2].metric("Delay chance", f"{probability:.0%}")
    st.write(connection_message)
    if has_connection and connection_label in {"High", "Very High"}:
        st.warning("Consider checking backup flights or asking the airline about rebooking options before departure.")
    elif has_connection:
        st.success("Your connection buffer looks acceptable for the current risk estimate.")
    else:
        st.info("Tick 'I have a connecting flight' in the form if you want connection advice.")

with map_tab:
    try:
        map_points, route_line = airport_map_rows(origin, dest, airports)
        midpoint_lat = float(map_points["lat"].mean())
        midpoint_lon = float(map_points["lon"].mean())
        if distance_miles >= 3200:
            route_zoom = 1.6
        elif distance_miles >= 1400:
            route_zoom = 2.4
        else:
            route_zoom = 3.6
        st.markdown(
            f"""
            <div class="journey-strip">
                <div class="journey-step">
                    <div class="kicker">Before you go</div>
                    <div class="headline">{leave_text}</div>
                    <div class="note">Leave for the airport</div>
                </div>
                <div class="journey-step">
                    <div class="kicker">Takeoff</div>
                    <div class="headline">{origin} at {selected_time:%H:%M}</div>
                    <div class="note">{airport_display_name(origin, airports)}</div>
                </div>
                <div class="journey-step">
                    <div class="kicker">Landing</div>
                    <div class="headline">{dest} around {destination_arrival_text}</div>
                    <div class="note">{airport_display_name(dest, airports)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="map-note">Flight path: about {distance_miles:,.0f} miles. Hover over each airport marker for details.</p>',
            unsafe_allow_html=True,
        )
        st.pydeck_chart(
            pdk.Deck(
                initial_view_state=pdk.ViewState(
                    latitude=midpoint_lat,
                    longitude=midpoint_lon,
                    zoom=route_zoom,
                    pitch=28,
                ),
                layers=[
                    pdk.Layer(
                        "ArcLayer",
                        data=route_line,
                        get_source_position="source",
                        get_target_position="target",
                        get_source_color=[20, 184, 166],
                        get_target_color=[249, 115, 22],
                        get_width=5,
                    ),
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=map_points,
                        get_position="[lon, lat]",
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        get_line_width=4,
                        get_radius=90000,
                        pickable=True,
                    ),
                    pdk.Layer(
                        "TextLayer",
                        data=map_points,
                        get_position="[lon, lat]",
                        get_text="text",
                        get_size=16,
                        get_color=[15, 23, 42],
                        get_angle=0,
                        get_text_anchor='"middle"',
                        get_alignment_baseline='"bottom"',
                    ),
                ],
                tooltip={"text": "{label}: {code}\n{name}"},
            )
        )
        st.dataframe(
            map_points[["label", "code", "name", "lat", "lon"]],
            hide_index=True,
            width="stretch",
        )
    except WeatherFetchError as exc:
        st.warning(f"Map unavailable: {exc}")

with destination_tab:
    st.markdown(f"### Travel Tips Blog: {destination_place}")
    st.caption(f"Destination city based on {dest} - {airport_display_name(dest, airports)}.")

    overview: dict[str, str] = {}
    guide: dict[str, str] = {}
    eat_text = ""
    buy_text = ""

    try:
        overview = fetch_wikipedia_summary(destination_place)
    except DestinationInfoError as exc:
        st.info(str(exc))
    try:
        guide = fetch_wikivoyage_tips(destination_place)
    except DestinationInfoError:
        guide = {}
    try:
        eat_text = fetch_wikivoyage_section_text(destination_place, ("Eat", "Drink"))
    except DestinationInfoError:
        eat_text = ""
    try:
        buy_text = fetch_wikivoyage_section_text(destination_place, ("Buy", "Shop"))
    except DestinationInfoError:
        buy_text = ""

    highlight_source = guide.get("extract") or overview.get("extract") or ""
    highlights = sentence_points(highlight_source, 3) or [
        f"Explore the main city area around {destination_place}.",
        "Check transport time from the airport before you land.",
        "Save a few nearby places before your flight in case mobile data is slow on arrival.",
    ]
    facts = destination_fun_facts(
        destination_place,
        overview.get("extract", ""),
        dest,
        airport_display_name(dest, airports),
        distance_miles,
    )

    top_cols = st.columns([1.25, 0.75], gap="large")
    with top_cols[0]:
        st.markdown("##### Quick Highlights")
        st.markdown("\n".join(f"- {item}" for item in highlights[:3]))
        st.markdown("##### Fun Facts")
        st.markdown("\n".join(f"- {fact}" for fact in facts[:3]))
    with top_cols[1]:
        image_url = overview.get("image", "")
        image_caption = destination_place
        if not image_url:
            try:
                image = fetch_commons_image(f"{destination_place} skyline landmark travel")
                image_url = image["url"]
                image_caption = image["title"]
            except DestinationInfoError:
                image_url = fallback_image_url(destination_place)
        st.image(image_url, caption=image_caption, width=300)

    food_cols = st.columns(2, gap="medium")
    with food_cols[0]:
        st.markdown("##### Eat: Current Finds")
        try:
            food_image = fetch_commons_image(f"{destination_place} food cuisine")
            st.image(food_image["url"], caption=food_image["title"], width=260)
        except DestinationInfoError:
            st.image(fallback_image_url(f"{destination_place} food"), caption=f"{destination_place} food", width=260)
        try:
            food_updates = fetch_destination_topic_updates(destination_place, "best restaurants food dining latest", max_items=2)
            st.markdown(
                "\n".join(
                    f"- [{markdown_link_text(item['title'])}]({item['link']})"
                    for item in food_updates
                )
            )
        except DestinationInfoError:
            st.markdown("\n".join(f"- {item}" for item in culinary_recommendations(destination_place, eat_text)[:2]))

    with food_cols[1]:
        st.markdown("##### Shop: Current Finds")
        try:
            souvenir_image = fetch_commons_image(f"{destination_place} market souvenirs")
            st.image(souvenir_image["url"], caption=souvenir_image["title"], width=260)
        except DestinationInfoError:
            st.image(fallback_image_url(f"{destination_place} souvenirs"), caption=f"{destination_place} souvenirs", width=260)
        try:
            shop_updates = fetch_destination_topic_updates(destination_place, "shopping souvenirs market latest", max_items=2)
            st.markdown(
                "\n".join(
                    f"- [{markdown_link_text(item['title'])}]({item['link']})"
                    for item in shop_updates
                )
            )
        except DestinationInfoError:
            st.markdown("\n".join(f"- {item}" for item in souvenir_recommendations(destination_place, buy_text)[:2]))

    st.markdown("##### Arrival Checklist")
    st.markdown(
        "\n".join(
            [
                f"- Check ground transport from {dest} before boarding, especially if you arrive late.",
                "- Save your hotel address and offline map before departure.",
                "- Re-check entry, visa, and document rules for international trips.",
            ]
        )
    )
    st.markdown("##### Local Transportation")
    st.markdown("\n".join(f"- {tip}" for tip in local_transportation_tips(destination_place, destination_country, dest)))
    transport_cols = st.columns(2)
    transport_cols[0].link_button(
        "Search airport transport",
        f"https://www.google.com/search?q={urllib.parse.quote_plus(dest + ' airport to ' + destination_place + ' train bus taxi')}",
    )
    transport_cols[1].link_button(
        "Open transit map search",
        f"https://www.google.com/maps/search/{urllib.parse.quote_plus(destination_place + ' public transport map')}",
    )
    st.markdown("##### Must Know: Rules And Visa")
    st.markdown(
        "\n".join(
            [
                f"- Destination country code: {destination_country or 'check destination country from your itinerary'}.",
                "- Visa and entry rules can change quickly. Check the official immigration or embassy website before departure.",
                "- Confirm passport validity, transit visa rules, customs limits, medication rules, and vaccination requirements.",
                "- Check what is forbidden before packing: controlled medicine, food, plants, alcohol/tobacco limits, cash limits, and restricted cultural items.",
                "- Keep digital and printed copies of your passport, booking, insurance, and return/onward ticket.",
            ]
        )
    )
    rules_cols = st.columns(2)
    rules_cols[0].link_button(
        "Search official visa rules",
        f"https://www.google.com/search?q={urllib.parse.quote_plus((destination_country or destination_place) + ' official visa entry requirements tourism')}",
    )
    rules_cols[1].link_button(
        "Search customs forbidden items",
        f"https://www.google.com/search?q={urllib.parse.quote_plus((destination_country or destination_place) + ' official customs prohibited items travelers')}",
    )
    try:
        rule_updates = fetch_destination_topic_updates(
            destination_place,
            "visa entry rules customs prohibited items travel advisory latest",
            max_items=3,
        )
        with st.expander("Latest rules and travel advisory links"):
            for item in rule_updates:
                render_news_card(item)
    except DestinationInfoError:
        st.info("Live visa/rules links are unavailable right now. Check official immigration and embassy websites before travel.")
    if guide.get("url"):
        st.link_button("Open full travel guide", guide["url"])

with travel_news_tab:
    st.markdown(f"#### {destination_place} Travel News")
    st.caption("Live headlines are loaded from public news feeds, so results may change over time.")
    news_cols = st.columns(2, gap="large")
    with news_cols[0]:
        st.markdown("##### Latest Travel News")
        try:
            news_items = fetch_destination_news(destination_place)
            for item in news_items[:4]:
                render_news_card(item)
        except DestinationInfoError as exc:
            st.info(str(exc))
    with news_cols[1]:
        st.markdown("##### Latest Viral / Trending")
        viral_items = fetch_social_trend_items(destination_place, max_items=4)
        if viral_items:
            for item in viral_items:
                render_news_card(item)
        else:
            st.info("No fresh viral feed item was returned, but you can open live platform searches below.")
        social_cols = st.columns(2)
        social_cols[0].link_button("Search TikTok", social_search_url("tiktok", destination_place))
        social_cols[1].link_button("Search Instagram", social_search_url("instagram", destination_place))

with booking_tab:
    st.markdown(f"#### Stay & Activities In {destination_place}")
    st.caption("Quick links open live booking/search pages for the destination city. Confirm price, reviews, location, and refund policy before paying.")
    hotel_urls = hotel_booking_urls(destination_place, selected_date)
    activity_url = klook_activity_url(destination_place)
    google_activity_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(destination_place + ' activities tours tickets')}"
    hotel_items = fetch_osm_recommendations(dest_latitude, dest_longitude, destination_place, "hotel", max_items=5)
    if not hotel_items:
        hotel_items = wikivoyage_recommendation_items(destination_place, ("Sleep",), "hotel", max_items=5)
    if not hotel_items:
        hotel_items = [
            {
                "name": f"Top-rated hotels in {destination_place}",
                "detail": "Open live hotel comparison to choose a specific property",
                "url": hotel_urls["Google Hotels"],
            }
        ]
    activity_items = fetch_osm_recommendations(dest_latitude, dest_longitude, destination_place, "activity", max_items=5)
    if not activity_items:
        activity_items = wikivoyage_recommendation_items(destination_place, ("See", "Do"), "activity", max_items=5)
    if not activity_items:
        activity_items = [
            {
                "name": f"Popular attractions in {destination_place}",
                "detail": "Open live activity search to choose a specific attraction",
                "url": google_activity_url,
            }
        ]

    stay_col, activity_col = st.columns(2, gap="large")
    with stay_col:
        st.markdown(
            f"""
            <div class="hotel-activity-card">
                <h5>Hotel Recommendations</h5>
                <div class="booking-note">Named hotel options from OpenStreetMap/Wikivoyage where available. Check reviews and cancellation before booking.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("##### Top 5 Hotels At A Glance")
        hotel_lines = []
        hotel_link_lines = []
        for item in hotel_items[:5]:
            hotel_search = booking_hotel_url(f"{item['name']} {destination_place}", selected_date)
            hotel_lines.append(f"- **{item['name']}** - {item.get('detail', 'Hotel option')}.")
            hotel_link_lines.append(f"- [{item['name']} info]({item['url']}) | [Book/search]({hotel_search})")
        st.markdown("\n".join(hotel_lines))
        with st.expander("Hotel booking links"):
            st.markdown("\n".join(hotel_link_lines))
    with activity_col:
        st.markdown(
            f"""
            <div class="hotel-activity-card">
                <h5>Activity & Attraction Recommendations</h5>
                <div class="booking-note">Named attractions near the destination area. Choose flexible time slots if your delay risk is moderate or high.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("##### Top 5 Attractions At A Glance")
        activity_lines = []
        activity_link_lines = []
        for item in activity_items[:5]:
            klook_search = klook_activity_url(f"{item['name']} {destination_place}")
            activity_lines.append(f"- **{item['name']}** - {item.get('detail', 'Attraction')}.")
            activity_link_lines.append(f"- [{item['name']} info]({item['url']}) | [Book/search]({klook_search})")
        st.markdown("\n".join(activity_lines))
        with st.expander("Attraction and activity links"):
            st.markdown("\n".join(activity_link_lines))

    st.markdown("##### Destination Mini Map")
    recommendation_map = destination_recommendation_map_rows(
        dest,
        destination_place,
        dest_latitude,
        dest_longitude,
        hotel_items,
        activity_items,
    )
    if len(recommendation_map) > 1:
        st.caption("Pink pins are hotels, orange pins are attractions, and teal marks the destination airport area.")
        st.pydeck_chart(
            pdk.Deck(
                initial_view_state=pdk.ViewState(
                    latitude=float(recommendation_map["lat"].mean()),
                    longitude=float(recommendation_map["lon"].mean()),
                    zoom=10,
                    pitch=0,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=recommendation_map,
                        get_position="[lon, lat]",
                        get_fill_color="color",
                        get_line_color=[255, 255, 255],
                        get_line_width=3,
                        get_radius="radius",
                        pickable=True,
                    ),
                    pdk.Layer(
                        "TextLayer",
                        data=recommendation_map,
                        get_position="[lon, lat]",
                        get_text="text",
                        get_size=16,
                        get_color=[15, 23, 42],
                        get_text_anchor='"middle"',
                        get_alignment_baseline='"bottom"',
                    ),
                ],
                tooltip={"text": "{type}: {name}"},
            )
        )
    else:
        st.info("Map pins are unavailable for these live recommendations, but the destination area is still searchable below.")
    st.link_button(
        "Open destination area in Google Maps",
        f"https://www.google.com/maps/search/{urllib.parse.quote_plus(destination_place + ' hotels attractions')}",
    )

    st.markdown("##### Compare Hotel Booking Sites")
    hotel_button_cols = st.columns(3)
    for idx, (provider, url) in enumerate(hotel_urls.items()):
        with hotel_button_cols[idx % 3]:
            st.link_button(provider, url)

    st.markdown("##### Compare Activities")
    activity_buttons = st.columns(2)
    activity_buttons[0].link_button("Klook activities", activity_url)
    activity_buttons[1].link_button("Google activities", google_activity_url)

    st.info("Tip: if delay risk is moderate or high, choose flexible hotel cancellation and avoid prepaid timed activities on arrival day.")

with airline_tab:
    st.markdown(f"#### {airline_label} At A Glance")
    st.caption(f"Airline code: {airline_code}. {airline_source_label}")
    airline_cols = st.columns([1.25, 0.75], gap="large")
    airline_overview: dict[str, str] = {}
    with airline_cols[0]:
        st.markdown("##### Quick Airline Info")
        try:
            airline_overview = fetch_wikipedia_summary(airline_label)
            st.write(short_text(airline_overview["extract"], 520))
            facts = sentence_points(airline_overview["extract"], 3)
            if facts:
                st.markdown("##### Fun Facts")
                st.markdown("\n".join(f"- {fact}" for fact in facts))
        except DestinationInfoError:
            st.info("Airline overview is unavailable right now.")
        st.markdown("##### Passenger Notes")
        st.markdown(
            "\n".join(
                [
                    "- Use the airline app or website as the final source for gate, boarding, baggage, and rebooking details.",
                    "- If the risk is high, turn on push notifications before leaving for the airport.",
                    "- For codeshare flights, check both the marketing airline and operating airline shown on your booking.",
                ]
            )
        )
        st.markdown("##### Fleet & Aviation Geek Notes")
        try:
            fleet_items = fetch_destination_topic_updates(
                airline_label,
                "fleet aircraft order cabin route network latest",
                max_items=3,
            )
            for item in fleet_items:
                render_news_card(item)
        except DestinationInfoError:
            st.markdown(
                "\n".join(
                    [
                        "- Fleet information changes when airlines retire, lease, or receive aircraft.",
                        "- Search specialist aviation databases for aircraft types, registrations, and delivery history.",
                    ]
                )
            )
    with airline_cols[1]:
        airline_image = airline_overview.get("image", "")
        image_caption = airline_label
        if not airline_image:
            try:
                image = fetch_commons_image(f"{airline_label} aircraft")
                airline_image = image["url"]
                image_caption = image["title"]
            except DestinationInfoError:
                airline_image = fallback_image_url(airline_label)
        st.image(airline_image, caption=image_caption, width=300)
        st.link_button("Search airline live status", f"https://www.google.com/search?q={urllib.parse.quote_plus(airline_label + ' flight status')}")
        st.link_button("Search FlightRadar24", f"https://www.google.com/search?q={urllib.parse.quote_plus(airline_label + ' FlightRadar24')}")
        st.link_button("Search fleet database", f"https://www.planespotters.net/search?q={urllib.parse.quote_plus(airline_label)}")
        st.link_button("Search aircraft types", f"https://www.google.com/search?q={urllib.parse.quote_plus(airline_label + ' fleet aircraft types')}")

with details_tab:
    translated_summary = translate_dataframe(summary, selected_language)
    st.dataframe(translated_summary, hide_index=True, width="stretch")
    st.download_button(
        "Download travel summary",
        data=csv_bytes(translated_summary),
        file_name="passenger_flight_delay_summary.csv",
        mime="text/csv",
    )

st.markdown(
    f"""
    <footer class="app-footer">
        <div class="footer-grid">
            <div>
                <h4>Passenger Flight Delay Assistant</h4>
                <p>Passenger-friendly flight delay risk, weather, booking comparison, destination tips, and travel planning in one demo.</p>
                <p>Selected language: {escape(selected_language)}<br>Selected currency: {escape(selected_currency)}</p>
            </div>
            <div>
                <h5>Privacy Policy</h5>
                <p>This demo does not sell personal data. Flight inputs are used to generate the current on-screen recommendation and may be sent to configured APIs only for lookup, weather, translation, or travel information.</p>
                <h5>Cookie Notice</h5>
                <p>Deployed Streamlit hosting or third-party booking links may use their own cookies and analytics.</p>
            </div>
            <div>
                <h5>Terms & Conditions</h5>
                <p>Use this tool for planning support only. External booking, hotel, activity, map, and news links are provided for convenience and are governed by their own terms.</p>
                <h5>Travel Disclaimer</h5>
                <p>Delay risk and prices are estimates for planning only. They are not airline, airport, hotel, visa, or government guarantees.</p>
            </div>
            <div>
                <h5>Data Sources</h5>
                <p>Weather: Open-Meteo<br>Flight lookup: Aviationstack when configured<br>Maps and places: OpenStreetMap, Wikivoyage, Wikimedia</p>
                <h5>Contact</h5>
                <p>For project questions, use the repository or deployment contact configured by the app owner.</p>
            </div>
        </div>
        <div class="footer-bottom">
            Copyright &copy; {date.today().year} Passenger Flight Delay Assistant. Educational demo for travel planning support.
        </div>
    </footer>
    """,
    unsafe_allow_html=True,
)

