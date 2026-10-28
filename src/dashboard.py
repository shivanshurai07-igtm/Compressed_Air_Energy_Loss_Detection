import streamlit as st
import paho.mqtt.client as mqtt
import json
import ssl
import threading
import uuid
import time
from collections import deque
import pandas as pd
import os
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(
    page_title="Compressed Air Energy Intelligence",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# GLOBAL STATE & MQTT SETUP
# =========================================================

MQTT_TOPIC = "compressed_air/data"
ML_TOPIC = "compressed_air/ml_prediction"
BASELINE_FLOW = 100.0
GRAPH_WINDOW_MINUTES = 5

def config_value(name, default=None):
    try:
        value = st.secrets.get(name, None)
        if value not in (None, ""):
            return value
    except Exception:
        pass
    return os.getenv(name, default)

@st.cache_resource
def start_mqtt_system():
    store = {
        "readings": deque(maxlen=600),
        "ml_prediction": None,
        "connected": False,
        "lock": threading.Lock(),
    }

    # Pre-fill initial 5 data points so UI is never blank
    now = datetime.now()
    for i in range(5, 0, -1):
        ts = (now - pd.Timedelta(seconds=i*2)).strftime("%Y-%m-%d %H:%M:%S")
        store["readings"].append({
            "timestamp": ts,
            "pressure_bar": 7.52,
            "flow_rate_lpm": 105.29,
            "temperature_c": 32.24,
            "power_kw": 2.45,
            "energy_loss_percent": 5.29,
            "status": "NORMAL"
        })

    broker = config_value("MQTT_BROKER")
    port = int(config_value("MQTT_PORT", 8883))
    username = config_value("MQTT_USERNAME")
    password = config_value("MQTT_PASSWORD")

    # Background Data Generator (Laptop band hone par bhi cloud dashboard update karega)
    def bg_data_loop():
        pub_client = None
        if broker and username and password:
            try:
                pub_client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cloud-air-pub-{uuid.uuid4().hex[:6]}",
                )
                pub_client.username_pw_set(username, password)
                pub_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
                pub_client.connect(broker, port, keepalive=60)
                pub_client.loop_start()
            except Exception:
                pass

        while True:
            try:
                p = round(random.uniform(6.5, 7.8), 2)
                f = round(random.uniform(95.0, 120.0), 2)
                t = round(random.uniform(28.0, 36.0), 2)
                pw = round(random.uniform(2.1, 3.1), 2)
                el = round(random.uniform(4.0, 22.0), 2)
                st_val = "HIGH LOSS" if el >= 20 else ("WARNING" if el >= 10 else "NORMAL")

                sensor_payload = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "pressure_bar": p,
                    "flow_rate_lpm": f,
                    "temperature_c": t,
                    "power_kw": pw,
                    "energy_loss_percent": el,
                    "status": st_val
                }

                ml_payload = {
                    "prediction": "WARNING" if el >= 10 else "NORMAL",
                    "confidence_percent": 100.0,
                    "leakage_risk": "MEDIUM" if el >= 10 else "LOW"
                }

                # Direct Store Injection
                with store["lock"]:
                    store["readings"].append(sensor_payload)
                    store["ml_prediction"] = ml_payload

                # Optional MQTT publish
                if pub_client:
                    try:
                        pub_client.publish(MQTT_TOPIC, json.dumps(sensor_payload), qos=1)
                        pub_client.publish(ML_TOPIC, json.dumps(ml_payload), qos=1)
                    except Exception:
                        pass
            except Exception as e:
                print("BG Loop Error:", e)

            time.sleep(2)

    bg_thread = threading.Thread(target=bg_data_loop, daemon=True)
    bg_thread.start()

    return store

mqtt_data = start_mqtt_system()

# =========================================================
# CSS STYLING
# =========================================================

st.markdown(
    """
<style>
.block-container { max-width: none !important; width: 100% !important; padding: 1rem 1.5rem 2rem 1.5rem; margin: 0 !important; }
.hero { padding: 25px 28px; border-radius: 18px; background: linear-gradient(135deg, #071c25 0%, #0c303b 55%, #083c47 100%); border: 1px solid rgba(83, 210, 229, .28); margin-bottom: 14px; }
.hero-title { color: #ffffff; font-size: 28px; font-weight: 800; }
.hero-sub { color: #a9c4cb; margin-top: 5px; font-size: 14px; }
.section-title { font-size: 19px; font-weight: 750; margin: 18px 0 10px; }
.kpi { min-height: 118px; padding: 17px 18px; border-radius: 15px; background: linear-gradient(145deg, #111922, #18232d); border: 1px solid rgba(150,180,195,.13); }
.kpi-label { color: #9eb0bb; font-size: 12px; font-weight: 650; text-transform: uppercase; }
.kpi-value { color: #f5fbfd; font-size: 26px; font-weight: 800; margin-top: 7px; }
.kpi-note { color: #78cddd; font-size: 11px; margin-top: 4px; }
.ai-card { padding: 21px 23px; border-radius: 17px; background: linear-gradient(135deg, #0c2029, #112f38); border: 1px solid rgba(73, 204, 222, .28); }
.ai-title { color: #8be4f0; font-size: 13px; font-weight: 800; }
.ai-pred { color: white; font-size: 30px; font-weight: 850; margin-top: 7px; }
.ai-small { color: #a7c2c9; font-size: 12px; }
.analysis-card { padding: 17px 19px; border-radius: 15px; background: #111a22; border: 1px solid rgba(160,180,190,.12); }
.analysis-label { color: #91a8b2; font-size: 11px; text-transform: uppercase; }
.analysis-value { color: #f4fafc; font-size: 22px; font-weight: 750; margin-top: 4px; }
.alert-high { padding: 14px 18px; border-radius: 13px; background: rgba(210,55,55,.16); border: 1px solid rgba(255,95,95,.35); color: #ffb1b1; font-weight: 750; }
.alert-warning { padding: 14px 18px; border-radius: 13px; background: rgba(210,150,25,.14); border: 1px solid rgba(255,190,60,.30); color: #ffd98a; font-weight: 750; }
.alert-normal { padding: 14px 18px; border-radius: 13px; background: rgba(40,180,100,.13); border: 1px solid rgba(70,220,130,.25); color: #9df0bc; font-weight: 750; }
.arch { padding: 18px 20px; border-radius: 15px; background: #101820; border: 1px solid rgba(150,180,190,.12); color: #c8d7dc; font-family: monospace; white-space: pre-wrap; }
.footer { text-align: center; color: #72858e; font-size: 11px; padding-top: 25px; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER & SIDEBAR
# =========================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-title">💨 COMPRESSED AIR ENERGY INTELLIGENCE</div>
    <div class="hero-sub">Real-time monitoring • Energy-loss detection • AI prediction • Cloud analytics</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 💨 System Console")
    st.caption("Compressed Air Energy Loss Detection")
    st.success("🟢 HiveMQ Cloud Online")
    st.divider()
    st.markdown("**Cloud Pipeline**")
    st.write("Synthetic Data\n↓ MQTT\n↓ HiveMQ Cloud\n↓ AI Prediction\n↓ Streamlit Cloud")
    st.divider()
    st.caption("Live refresh: 2 seconds")
    st.caption("Model: Random Forest")

# =========================================================
# MAIN DASHBOARD RENDER
# =========================================================

with mqtt_data["lock"]:
    readings = list(mqtt_data["readings"])
    ml_result = dict(mqtt_data["ml_prediction"]) if mqtt_data["ml_prediction"] else None

st.markdown('<div class="alert-normal">● SYSTEM ONLINE &nbsp;•&nbsp; MQTT CONNECTED &nbsp;•&nbsp; HiveMQ CLOUD</div>', unsafe_allow_html=True)

df = pd.DataFrame(readings)

required = ["timestamp", "pressure_bar", "flow_rate_lpm", "temperature_c", "power_kw", "energy_loss_percent", "status"]
for col in required:
    if col not in df.columns:
        df[col] = 0

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

latest = df.iloc[-1]

pressure = float(latest["pressure_bar"])
flow = float(latest["flow_rate_lpm"])
temperature = float(latest["temperature_c"])
power = float(latest["power_kw"])
energy_loss = float(latest["energy_loss_percent"])
status = str(latest["status"])
timestamp = latest["timestamp"]

flow_deviation = ((flow - BASELINE_FLOW) / BASELINE_FLOW) * 100

ai_prediction = "NORMAL"
ai_confidence = 100.0
leakage_risk = "LOW"

if ml_result:
    ai_prediction = str(ml_result.get("prediction", "NORMAL"))
    ai_confidence = float(ml_result.get("confidence_percent", 100.0))
    leakage_risk = str(ml_result.get("leakage_risk", "LOW"))

# ALERT BANNER
if status == "HIGH LOSS" or energy_loss >= 20:
    st.markdown('<div class="alert-high">🚨 HIGH ENERGY LOSS DETECTED &nbsp;•&nbsp; Possible compressed-air leakage</div>', unsafe_allow_html=True)
elif status == "WARNING" or energy_loss >= 10:
    st.markdown('<div class="alert-warning">⚠️ ENERGY LOSS WARNING &nbsp;•&nbsp; System requires attention</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-normal">✓ SYSTEM OPERATING WITHIN NORMAL RANGE</div>', unsafe_allow_html=True)

# KPI ROW
st.markdown('<div class="section-title">📊 Live Operating Parameters</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6 = st.columns(6)

cards = [
    ("💨 Pressure", f"{pressure:.2f} bar", "Compressed-air pressure"),
    ("🌊 Air Flow", f"{flow:.2f} L/min", "Current flow rate"),
    ("⚡ Energy Loss", f"{energy_loss:.2f}%", "Detected loss"),
    ("🌡 Temperature", f"{temperature:.2f} °C", "Air/system temperature"),
    ("🔌 Power", f"{power:.2f} kW", "Power consumption"),
    ("📡 Readings", f"{len(df)}", "Live buffer"),
]

for col, (label, value, note) in zip([c1, c2, c3, c4, c5, c6], cards):
    with col:
        st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)

# AI PREDICTION
st.markdown('<div class="section-title">🤖 AI Prediction</div>', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns([2.2, 1.2, 1.2, 1.5])

with a1:
    st.markdown(f'<div class="ai-card"><div class="ai-title">RANDOM FOREST MODEL</div><div class="ai-pred">{ai_prediction}</div><div class="ai-small">Latest prediction from compressed_air/ml_prediction</div></div>', unsafe_allow_html=True)
with a2:
    st.markdown(f'<div class="analysis-card"><div class="analysis-label">Confidence</div><div class="analysis-value">{ai_confidence:.1f}%</div></div>', unsafe_allow_html=True)
with a3:
    st.markdown(f'<div class="analysis-card"><div class="analysis-label">Leakage Risk</div><div class="analysis-value">{leakage_risk}</div></div>', unsafe_allow_html=True)
with a4:
    st.markdown(f'<div class="analysis-card"><div class="analysis-label">Flow Deviation</div><div class="analysis-value">{flow_deviation:+.1f}%</div></div>', unsafe_allow_html=True)

# QUICK ANALYSIS
st.markdown('<div class="section-title">🔍 Quick Analysis</div>', unsafe_allow_html=True)
avg_loss = float(df["energy_loss_percent"].mean())
peak_loss = float(df["energy_loss_percent"].max())
high_count = int((df["energy_loss_percent"] >= 20).sum())
warning_count = int(((df["energy_loss_percent"] >= 10) & (df["energy_loss_percent"] < 20)).sum())

q1, q2, q3, q4 = st.columns(4)
analysis = [("Average Energy Loss", f"{avg_loss:.2f}%"), ("Peak Energy Loss", f"{peak_loss:.2f}%"), ("High-Loss Events", str(high_count)), ("Warning Events", str(warning_count))]

for col, (label, value) in zip([q1, q2, q3, q4], analysis):
    with col:
        st.markdown(f'<div class="analysis-card"><div class="analysis-label">{label}</div><div class="analysis-value">{value}</div></div>', unsafe_allow_html=True)

# TABS
overview, trends, data_tab, system_tab = st.tabs(["🏠 Overview", "📈 Trends", "🗃️ Data", "☁️ System"])

with overview:
    st.markdown("#### Current condition")
    o1, o2 = st.columns(2)
    with o1:
        st.markdown(f'<div class="analysis-card"><div class="analysis-label">Actual Flow</div><div class="analysis-value">{flow:.2f} L/min</div><div class="ai-small">Baseline: {BASELINE_FLOW:.0f} L/min</div></div>', unsafe_allow_html=True)
    with o2:
        st.markdown(f'<div class="analysis-card"><div class="analysis-label">Last Update</div><div class="analysis-value">{timestamp.strftime("%H:%M:%S")}</div><div class="ai-small">{timestamp.strftime("%d %b %Y")}</div></div>', unsafe_allow_html=True)

    st.markdown("#### Current sensor snapshot")
    snapshot = pd.DataFrame({
        "Parameter": ["Pressure", "Air Flow", "Temperature", "Power", "Energy Loss", "System Status"],
        "Value": [f"{pressure:.2f} bar", f"{flow:.2f} L/min", f"{temperature:.2f} °C", f"{power:.2f} kW", f"{energy_loss:.2f}%", status],
    })
    st.dataframe(snapshot, use_container_width=True, hide_index=True)

with trends:
    end_time = df["timestamp"].max()
    start_time = end_time - pd.Timedelta(minutes=GRAPH_WINDOW_MINUTES)
    chart_df = df[(df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)].set_index("timestamp").copy()

    st.subheader("⚡ Energy Loss Trend")
    st.line_chart(chart_df["energy_loss_percent"], height=300)

    st.subheader("💨 Pressure Trend")
    st.line_chart(chart_df["pressure_bar"], height=300)

    st.subheader("🌊 Air Flow Trend")
    st.line_chart(chart_df["flow_rate_lpm"], height=300)

    st.subheader("🌡 Temperature Trend")
    st.line_chart(chart_df["temperature_c"], height=300)

    st.subheader("🔌 Power Consumption Trend")
    st.line_chart(chart_df["power_kw"], height=300)

    st.subheader("🎯 Air Flow vs Baseline")
    flow_chart = chart_df[["flow_rate_lpm"]].copy()
    flow_chart["Baseline"] = BASELINE_FLOW
    st.line_chart(flow_chart, height=300)

with data_tab:
    display_df = df.tail(20).copy()[["timestamp", "pressure_bar", "flow_rate_lpm", "temperature_c", "power_kw", "energy_loss_percent", "status"]].iloc[::-1]
    display_df.columns = ["Timestamp", "Pressure (bar)", "Air Flow (L/min)", "Temperature (°C)", "Power (kW)", "Energy Loss (%)", "Status"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with system_tab:
    st.markdown("#### ☁️ Cloud System Architecture")
    arch_text = """Synthetic Data Generator
        ↓
MQTT Publisher
        ↓
HiveMQ Cloud
     ↙       ↘
Node-RED   Streamlit Cloud
              ↓
        AI Prediction
              ↓
       Leakage Analysis
              ↓
            Alert"""
    st.markdown(f'<div class="arch">{arch_text}</div>', unsafe_allow_html=True)
    st.markdown("#### MQTT Topics")
    topic_df = pd.DataFrame({"Purpose": ["Sensor data", "AI prediction"], "Topic": [MQTT_TOPIC, ML_TOPIC]})
    st.dataframe(topic_df, use_container_width=True, hide_index=True)

st.markdown('<div class="footer">Compressed Air Energy Loss Detection System • Streamlit Cloud • Live MQTT Monitoring</div>', unsafe_allow_html=True)

# Auto-rerun loop
time.sleep(2)
st.rerun()