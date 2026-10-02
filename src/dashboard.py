import streamlit as st
import paho.mqtt.client as mqtt
import json
import ssl
import threading
import uuid
import time
from collections import deque
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Compressed Air Energy Intelligence",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# MQTT
# =========================================================

MQTT_TOPIC = "compressed_air/data"
ML_TOPIC = "compressed_air/ml_prediction"
BASELINE_FLOW = 100.0
GRAPH_WINDOW_MINUTES = 5


@st.cache_resource
def start_mqtt():
    store = {
        "readings": deque(maxlen=600),
        "ml_prediction": None,
        "connected": False,
        "last_disconnect": 0.0,
        "lock": threading.Lock(),
    }

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            with store["lock"]:
                store["connected"] = True
                store["last_disconnect"] = 0.0

            client.subscribe(MQTT_TOPIC, qos=1)
            client.subscribe(ML_TOPIC, qos=1)
            print("Connected to HiveMQ Cloud")
        else:
            with store["lock"]:
                store["connected"] = False
            print("MQTT connection failed:", reason_code)

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
        # Do not immediately flash the UI red during a reconnect.
        with store["lock"]:
            store["last_disconnect"] = time.time()
        print("MQTT disconnected:", reason_code)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))

            with store["lock"]:
                if message.topic == ML_TOPIC:
                    store["ml_prediction"] = payload
                elif message.topic == MQTT_TOPIC:
                    store["readings"].append(payload)

        except Exception as exc:
            print("MQTT message error:", exc)

    # Local: read MQTT credentials from .env
    # Streamlit Cloud: read the same values from Streamlit Secrets.
    def config_value(name, default=None):
        try:
            value = st.secrets.get(name, None)
            if value not in (None, ""):
                return value
        except Exception:
            pass
        return os.getenv(name, default)

    broker = config_value("MQTT_BROKER")
    port = int(config_value("MQTT_PORT", 8883))
    username = config_value("MQTT_USERNAME")
    password = config_value("MQTT_PASSWORD")

    if not broker or not username or not password:
        raise RuntimeError(
            "MQTT credentials not found. "
            "For local run, check your .env file. "
            "For Streamlit Cloud, add MQTT_BROKER, MQTT_PORT, "
            "MQTT_USERNAME and MQTT_PASSWORD in Secrets."
        )

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"cloud-air-dashboard-{uuid.uuid4().hex[:10]}",
    )

    client.username_pw_set(username, password)

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT,
    )

    client.reconnect_delay_set(min_delay=1, max_delay=15)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(broker, port, keepalive=60)
        client.loop_start()
    except Exception as exc:
        print("MQTT connection error:", exc)

    return store


mqtt_data = start_mqtt()

# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
<style>
.block-container {
    max-width: none !important;
    width: 100% !important;
    padding: 1rem 1.5rem 2rem 1.5rem;
    margin: 0 !important;
}

section[data-testid="stMain"] > div,
[data-testid="stAppViewContainer"] > section > div,
[data-testid="stMainBlockContainer"] {
    max-width: none !important;
    width: 100% !important;
}

[data-testid="stMainBlockContainer"] > div {
    width: 100% !important;
}

.hero {
    padding: 25px 28px;
    border-radius: 18px;
    background: linear-gradient(135deg, #071c25 0%, #0c303b 55%, #083c47 100%);
    border: 1px solid rgba(83, 210, 229, .28);
    box-shadow: 0 10px 35px rgba(0,0,0,.18);
    margin-bottom: 14px;
}

.hero-title {
    color: #ffffff;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: .6px;
}

.hero-sub {
    color: #a9c4cb;
    margin-top: 5px;
    font-size: 14px;
}

.section-title {
    font-size: 19px;
    font-weight: 750;
    margin: 18px 0 10px;
}

.kpi {
    min-height: 118px;
    padding: 17px 18px;
    border-radius: 15px;
    background: linear-gradient(145deg, #111922, #18232d);
    border: 1px solid rgba(150,180,195,.13);
    box-shadow: 0 6px 20px rgba(0,0,0,.12);
}

.kpi-label {
    color: #9eb0bb;
    font-size: 12px;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.kpi-value {
    color: #f5fbfd;
    font-size: 26px;
    font-weight: 800;
    margin-top: 7px;
}

.kpi-note {
    color: #78cddd;
    font-size: 11px;
    margin-top: 4px;
}

.ai-card {
    padding: 21px 23px;
    border-radius: 17px;
    background: linear-gradient(135deg, #0c2029, #112f38);
    border: 1px solid rgba(73, 204, 222, .28);
    box-shadow: 0 8px 28px rgba(0,0,0,.15);
}

.ai-title {
    color: #8be4f0;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1px;
}

.ai-pred {
    color: white;
    font-size: 30px;
    font-weight: 850;
    margin-top: 7px;
}

.ai-small {
    color: #a7c2c9;
    font-size: 12px;
}

.analysis-card {
    padding: 17px 19px;
    border-radius: 15px;
    background: #111a22;
    border: 1px solid rgba(160,180,190,.12);
}

.analysis-label {
    color: #91a8b2;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .7px;
}

.analysis-value {
    color: #f4fafc;
    font-size: 22px;
    font-weight: 750;
    margin-top: 4px;
}

.alert-high {
    padding: 14px 18px;
    border-radius: 13px;
    background: rgba(210,55,55,.16);
    border: 1px solid rgba(255,95,95,.35);
    color: #ffb1b1;
    font-weight: 750;
}

.alert-warning {
    padding: 14px 18px;
    border-radius: 13px;
    background: rgba(210,150,25,.14);
    border: 1px solid rgba(255,190,60,.30);
    color: #ffd98a;
    font-weight: 750;
}

.alert-normal {
    padding: 14px 18px;
    border-radius: 13px;
    background: rgba(40,180,100,.13);
    border: 1px solid rgba(70,220,130,.25);
    color: #9df0bc;
    font-weight: 750;
}

.arch {
    padding: 18px 20px;
    border-radius: 15px;
    background: #101820;
    border: 1px solid rgba(150,180,190,.12);
    color: #c8d7dc;
    font-family: monospace;
    line-height: 1.75;
}

.footer {
    text-align: center;
    color: #72858e;
    font-size: 11px;
    padding-top: 25px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-title">💨 COMPRESSED AIR ENERGY INTELLIGENCE</div>
    <div class="hero-sub">
        Real-time monitoring • Energy-loss detection • AI prediction • Cloud analytics
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("### 💨 System Console")
    st.caption("Compressed Air Energy Loss Detection")

    with mqtt_data["lock"]:
        connected = mqtt_data["connected"]
        last_disconnect = mqtt_data["last_disconnect"]

    if connected:
        st.success("🟢 HiveMQ Cloud Online")
    elif last_disconnect and time.time() - last_disconnect < 10:
        st.info("🟡 Reconnecting to HiveMQ...")
    else:
        st.error("🔴 MQTT Offline")

    st.divider()
    st.markdown("**Cloud Pipeline**")
    st.write("Synthetic Data")
    st.write("↓ MQTT")
    st.write("↓ HiveMQ Cloud")
    st.write("↓ AI Prediction")
    st.write("↓ Streamlit Cloud")

    st.divider()
    st.caption("Live refresh: 3 seconds")
    st.caption("Model: Random Forest")

# =========================================================
# LIVE DASHBOARD
# =========================================================

@st.fragment(run_every="5s")
def live_dashboard():

    with mqtt_data["lock"]:
        readings = list(mqtt_data["readings"])
        ml_result = dict(mqtt_data["ml_prediction"]) if mqtt_data["ml_prediction"] else None
        connected_now = mqtt_data["connected"]
        last_disconnect = mqtt_data["last_disconnect"]

    if connected_now:
        st.markdown(
            '<div class="alert-normal">● SYSTEM ONLINE &nbsp;•&nbsp; MQTT CONNECTED &nbsp;•&nbsp; HiveMQ CLOUD</div>',
            unsafe_allow_html=True,
        )
    elif last_disconnect and time.time() - last_disconnect < 10:
        st.info("🟡 Reconnecting to HiveMQ Cloud...")
    else:
        st.error("🔴 MQTT connection unavailable")

    if not readings:
        st.info("Waiting for sensor data from compressed_air/data ...")
        return

    df = pd.DataFrame(readings)

    required = [
        "timestamp",
        "pressure_bar",
        "flow_rate_lpm",
        "temperature_c",
        "power_kw",
        "energy_loss_percent",
        "status",
    ]

    for col in required:
        if col not in df.columns:
            df[col] = 0

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    if df.empty:
        st.warning("No valid timestamped readings available.")
        return

    latest = df.iloc[-1]

    pressure = float(latest["pressure_bar"])
    flow = float(latest["flow_rate_lpm"])
    temperature = float(latest["temperature_c"])
    power = float(latest["power_kw"])
    energy_loss = float(latest["energy_loss_percent"])
    status = str(latest["status"])
    timestamp = latest["timestamp"]

    flow_deviation = ((flow - BASELINE_FLOW) / BASELINE_FLOW) * 100

    # Prefer AI result from the ML topic; fall back to sensor status only for display.
    ai_prediction = "WAITING"
    ai_confidence = 0.0
    leakage_risk = "UNKNOWN"

    if ml_result:
        ai_prediction = str(
            ml_result.get("prediction", ml_result.get("ai_prediction", "WAITING"))
        )
        ai_confidence = float(
            ml_result.get("confidence_percent", ml_result.get("confidence", 0))
        )
        leakage_risk = str(
            ml_result.get("leakage_risk", "UNKNOWN")
        )

    # =====================================================
    # ALERT
    # =====================================================

    if status == "HIGH LOSS" or energy_loss >= 20:
        st.markdown(
            '<div class="alert-high">🚨 HIGH ENERGY LOSS DETECTED &nbsp;•&nbsp; Possible compressed-air leakage</div>',
            unsafe_allow_html=True,
        )
    elif status == "WARNING" or energy_loss >= 10:
        st.markdown(
            '<div class="alert-warning">⚠️ ENERGY LOSS WARNING &nbsp;•&nbsp; System requires attention</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="alert-normal">✓ SYSTEM OPERATING WITHIN NORMAL RANGE</div>',
            unsafe_allow_html=True,
        )

    # =====================================================
    # KPI ROW
    # =====================================================

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
            st.markdown(
                f"""
<div class="kpi">
    <div class="kpi-label">{label}</div>
    <div class="kpi-value">{value}</div>
    <div class="kpi-note">{note}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # =====================================================
    # AI PREDICTION — ONLY ONE SECTION
    # =====================================================

    st.markdown('<div class="section-title">🤖 AI Prediction</div>', unsafe_allow_html=True)

    a1, a2, a3, a4 = st.columns([2.2, 1.2, 1.2, 1.5])

    with a1:
        st.markdown(
            f"""
<div class="ai-card">
    <div class="ai-title">RANDOM FOREST MODEL</div>
    <div class="ai-pred">{ai_prediction}</div>
    <div class="ai-small">Latest prediction from compressed_air/ml_prediction</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with a2:
        st.markdown(
            f"""
<div class="analysis-card">
    <div class="analysis-label">Confidence</div>
    <div class="analysis-value">{ai_confidence:.1f}%</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with a3:
        st.markdown(
            f"""
<div class="analysis-card">
    <div class="analysis-label">Leakage Risk</div>
    <div class="analysis-value">{leakage_risk}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with a4:
        st.markdown(
            f"""
<div class="analysis-card">
    <div class="analysis-label">Flow Deviation</div>
    <div class="analysis-value">{flow_deviation:+.1f}%</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # =====================================================
    # QUICK ANALYSIS
    # =====================================================

    st.markdown('<div class="section-title">🔍 Quick Analysis</div>', unsafe_allow_html=True)

    avg_loss = float(df["energy_loss_percent"].mean())
    peak_loss = float(df["energy_loss_percent"].max())
    high_count = int((df["energy_loss_percent"] >= 20).sum())
    warning_count = int(
        ((df["energy_loss_percent"] >= 10) & (df["energy_loss_percent"] < 20)).sum()
    )

    q1, q2, q3, q4 = st.columns(4)

    analysis = [
        ("Average Energy Loss", f"{avg_loss:.2f}%"),
        ("Peak Energy Loss", f"{peak_loss:.2f}%"),
        ("High-Loss Events", str(high_count)),
        ("Warning Events", str(warning_count)),
    ]

    for col, (label, value) in zip([q1, q2, q3, q4], analysis):
        with col:
            st.markdown(
                f"""
<div class="analysis-card">
    <div class="analysis-label">{label}</div>
    <div class="analysis-value">{value}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # =====================================================
    # TABS
    # =====================================================

    overview, trends, data_tab, system_tab = st.tabs(
        ["🏠 Overview", "📈 Trends", "🗃️ Data", "☁️ System"]
    )

    with overview:
        st.markdown("#### Current condition")

        o1, o2 = st.columns(2)

        with o1:
            st.markdown(
                f"""
<div class="analysis-card">
    <div class="analysis-label">Actual Flow</div>
    <div class="analysis-value">{flow:.2f} L/min</div>
    <div class="ai-small">Baseline: {BASELINE_FLOW:.0f} L/min</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with o2:
            st.markdown(
                f"""
<div class="analysis-card">
    <div class="analysis-label">Last Update</div>
    <div class="analysis-value">{timestamp.strftime("%H:%M:%S")}</div>
    <div class="ai-small">{timestamp.strftime("%d %b %Y")}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.markdown("#### Current sensor snapshot")
        snapshot = pd.DataFrame(
            {
                "Parameter": [
                    "Pressure",
                    "Air Flow",
                    "Temperature",
                    "Power",
                    "Energy Loss",
                    "System Status",
                ],
                "Value": [
                    f"{pressure:.2f} bar",
                    f"{flow:.2f} L/min",
                    f"{temperature:.2f} °C",
                    f"{power:.2f} kW",
                    f"{energy_loss:.2f}%",
                    status,
                ],
            }
        )
        st.dataframe(snapshot, use_container_width=True, hide_index=True)

    with trends:
        end_time = df["timestamp"].max()
        start_time = end_time - pd.Timedelta(minutes=GRAPH_WINDOW_MINUTES)

        chart_df = (
            df[
                (df["timestamp"] >= start_time) &
                (df["timestamp"] <= end_time)
            ]
            .set_index("timestamp")
        )

        def make_smooth_chart(data, column, title, y_label, suffix="", baseline=None, thresholds=None):
            values = pd.to_numeric(data[column], errors="coerce").dropna()
            if values.empty:
                return

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=values.index,
                    y=values.values,
                    mode="lines",
                    name=title,
                    line=dict(shape="spline", smoothing=0.30, width=3),
                    hovertemplate=f"%{{x|%H:%M:%S}}<br>{y_label}: %{{y:.2f}}{suffix}<extra></extra>",
                )
            )

            if baseline is not None:
                fig.add_trace(
                    go.Scatter(
                        x=values.index,
                        y=[baseline] * len(values),
                        mode="lines",
                        name="Baseline",
                        line=dict(dash="dash", width=2),
                        hovertemplate=f"Baseline: {baseline:.0f}{suffix}<extra></extra>",
                    )
                )

            if thresholds:
                for threshold_value, threshold_name in thresholds:
                    fig.add_trace(
                        go.Scatter(
                            x=values.index,
                            y=[threshold_value] * len(values),
                            mode="lines",
                            name=threshold_name,
                            line=dict(dash="dot", width=1.5),
                            hovertemplate=f"{threshold_name}: {threshold_value:g}{suffix}<extra></extra>",
                        )
                    )

            vmin = float(values.min())
            vmax = float(values.max())
            span = max(vmax - vmin, abs(vmax) * 0.08, 0.5)
            pad = span * 0.18

            if baseline is not None:
                low = min(vmin, baseline)
                high = max(vmax, baseline)
                span = max(high - low, 1.0)
                pad = span * 0.15
                y_range = [low - pad, high + pad]
            else:
                y_range = [vmin - pad, vmax + pad]

            fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=38, b=10),
                title=dict(text=title, x=0.01, font=dict(size=16)),
                template="plotly_dark",
                uirevision="live",
                hovermode="x unified",
                showlegend=(baseline is not None or bool(thresholds)),
                legend=dict(orientation="h", y=1.08, x=0),
                xaxis=dict(
                    title="Time",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.08)",
                    rangeslider=dict(visible=False),
                ),
                yaxis=dict(
                    title=y_label,
                    range=y_range,
                    fixedrange=False,
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.08)",
                    zeroline=False,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                },
                key=f"chart_{column}_{title.replace(' ', '_')}",
            )

        st.caption(
            f"Live trend window: last {GRAPH_WINDOW_MINUTES} minutes • "
            f"Updates automatically every 5 seconds"
        )

        # Full-width charts, one per row — closer to the Node-RED trend layout.
        make_smooth_chart(
            chart_df, "energy_loss_percent",
            "⚡ Energy Loss Trend", "Energy Loss (%)", "%",
            thresholds=[
                (10, "Warning • 10%"),
                (20, "High Loss • 20%"),
            ],
        )
        make_smooth_chart(
            chart_df, "pressure_bar",
            "💨 Pressure Trend", "Pressure (bar)", " bar"
        )
        make_smooth_chart(
            chart_df, "flow_rate_lpm",
            "🌊 Air Flow Trend", "Air Flow (L/min)", " L/min"
        )
        make_smooth_chart(
            chart_df, "temperature_c",
            "🌡 Temperature Trend", "Temperature (°C)", " °C"
        )
        make_smooth_chart(
            chart_df, "power_kw",
            "🔌 Power Consumption Trend", "Power (kW)", " kW"
        )
        make_smooth_chart(
            chart_df, "flow_rate_lpm",
            "🎯 Air Flow vs Baseline", "Air Flow (L/min)", " L/min",
            baseline=BASELINE_FLOW
        )

    with data_tab:
        display_df = df.tail(20).copy()
        display_df = display_df[
            [
                "timestamp",
                "pressure_bar",
                "flow_rate_lpm",
                "temperature_c",
                "power_kw",
                "energy_loss_percent",
                "status",
            ]
        ].iloc[::-1]

        display_df.columns = [
            "Timestamp",
            "Pressure (bar)",
            "Air Flow (L/min)",
            "Temperature (°C)",
            "Power (kW)",
            "Energy Loss (%)",
            "Status",
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

    with system_tab:
        st.markdown("#### ☁️ Cloud System Architecture")
        st.markdown(
            """
<div class="arch">
Synthetic Data Generator
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
            Alert
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("#### MQTT Topics")
        topic_df = pd.DataFrame(
            {
                "Purpose": ["Sensor data", "AI prediction"],
                "Topic": [MQTT_TOPIC, ML_TOPIC],
            }
        )
        st.dataframe(topic_df, use_container_width=True, hide_index=True)

        st.caption(
            "AI Prediction is displayed once on this dashboard. "
            "The ML topic is consumed in the background."
        )

    st.markdown(
        '<div class="footer">Compressed Air Energy Loss Detection System • Streamlit Cloud • Live MQTT Monitoring</div>',
        unsafe_allow_html=True,
    )


live_dashboard()
