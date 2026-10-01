import streamlit as st
import pandas as pd
import json
import ssl
import os
import threading
from collections import deque

import paho.mqtt.client as mqtt


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Compressed Air Energy Monitoring",
    page_icon="💨",
    layout="wide"
)


# =========================================================
# MQTT CONFIGURATION
# =========================================================

MQTT_TOPIC = "compressed_air/data"

# Local .env for testing
# Streamlit Cloud will use st.secrets
try:
    MQTT_BROKER = st.secrets["MQTT_BROKER"]
    MQTT_PORT = int(st.secrets.get("MQTT_PORT", 8883))
    MQTT_USERNAME = st.secrets["MQTT_USERNAME"]
    MQTT_PASSWORD = st.secrets["MQTT_PASSWORD"]

except Exception:

    from dotenv import load_dotenv

    load_dotenv()

    MQTT_BROKER = os.getenv("MQTT_BROKER")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")


# =========================================================
# LIVE MQTT DATA STORE
# =========================================================

@st.cache_resource
def create_mqtt_connection():

    data_store = {
        "history": deque(maxlen=500),
        "lock": threading.Lock(),
        "connected": False
    }

    def on_connect(client, userdata, flags, rc, properties=None):

        if rc == 0:

            data_store["connected"] = True

            client.subscribe(MQTT_TOPIC)

        else:

            data_store["connected"] = False


    def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):

        data_store["connected"] = False


    def on_message(client, userdata, message):

        try:

            payload = json.loads(
                message.payload.decode("utf-8")
            )

            with data_store["lock"]:

                data_store["history"].append(payload)

        except Exception:

            pass


    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="streamlit-cloud-dashboard"
    )

    client.username_pw_set(
        MQTT_USERNAME,
        MQTT_PASSWORD
    )

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:

        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )

        client.loop_start()

    except Exception:

        data_store["connected"] = False


    return client, data_store


# =========================================================
# CONNECT TO MQTT
# =========================================================

client, data_store = create_mqtt_connection()


# =========================================================
# GET LIVE DATA
# =========================================================

with data_store["lock"]:

    history = list(data_store["history"])


if len(history) == 0:

    st.title("💨 Compressed Air Energy Monitoring System")

    st.caption(
        "Real-time monitoring using MQTT and HiveMQ Cloud"
    )

    st.divider()

    if data_store["connected"]:

        st.info(
            "🔄 Connected to HiveMQ Cloud. Waiting for sensor data..."
        )

    else:

        st.error(
            "❌ Unable to connect to HiveMQ Cloud."
        )

    st.stop()


# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(history)


# Make sure required columns exist

required_columns = [
    "timestamp",
    "pressure_bar",
    "flow_rate_lpm",
    "temperature_c",
    "power_kw",
    "energy_loss_percent",
    "status"
]

for column in required_columns:

    if column not in df.columns:

        df[column] = None


df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)


df = df.dropna(
    subset=["timestamp"]
)


df = df.sort_values(
    "timestamp"
)


# =========================================================
# LATEST READING
# =========================================================

latest = df.iloc[-1]


pressure = float(
    latest["pressure_bar"]
)

flow = float(
    latest["flow_rate_lpm"]
)

temperature = float(
    latest["temperature_c"]
)

power = float(
    latest["power_kw"]
)

energy_loss = float(
    latest["energy_loss_percent"]
)

status = latest["status"]

timestamp = latest["timestamp"]


# =========================================================
# HEADER
# =========================================================

st.title(
    "💨 Compressed Air Energy Monitoring System"
)

st.caption(
    "Real-time monitoring using MQTT and HiveMQ Cloud"
)


# MQTT connection status

if data_store["connected"]:

    st.success(
        "🟢 SYSTEM ONLINE • MQTT CONNECTED • HiveMQ CLOUD"
    )

else:

    st.error(
        "🔴 MQTT CONNECTION LOST"
    )


st.divider()


# =========================================================
# ENERGY LOSS STATUS
# =========================================================

if status == "HIGH LOSS":

    st.error(
        "🚨 HIGH ENERGY LOSS DETECTED"
    )

elif status == "WARNING":

    st.warning(
        "⚠️ ENERGY LOSS WARNING"
    )

else:

    st.success(
        "✅ SYSTEM NORMAL"
    )


# =========================================================
# METRICS
# =========================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Pressure",
        f"{pressure:.2f} bar"
    )


with col2:

    st.metric(
        "Air Flow",
        f"{flow:.2f} L/min"
    )


with col3:

    st.metric(
        "Energy Loss",
        f"{energy_loss:.2f}%"
    )


with col4:

    st.metric(
        "Live Readings",
        len(df)
    )


st.divider()


# =========================================================
# ADDITIONAL PARAMETERS
# =========================================================

st.subheader(
    "⚙️ Machine Parameters"
)

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Temperature",
        f"{temperature:.2f} °C"
    )


with col2:

    st.metric(
        "Power",
        f"{power:.2f} kW"
    )


with col3:

    st.metric(
        "System Status",
        status
    )


# =========================================================
# LAST UPDATE
# =========================================================

st.write(
    f"🕒 **Last Reading:** "
    f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
)


st.divider()


# =========================================================
# ENERGY LOSS GRAPH
# =========================================================

st.subheader(
    "📊 Energy Loss"
)

chart_df = df.set_index(
    "timestamp"
)

st.line_chart(
    chart_df["energy_loss_percent"],
    y_label="Energy Loss (%)"
)


# =========================================================
# PRESSURE GRAPH
# =========================================================

st.subheader(
    "💨 Pressure"
)

st.line_chart(
    chart_df["pressure_bar"],
    y_label="Pressure (bar)"
)


# =========================================================
# AIR FLOW GRAPH
# =========================================================

st.subheader(
    "🌊 Air Flow"
)

st.line_chart(
    chart_df["flow_rate_lpm"],
    y_label="Air Flow (L/min)"
)


# =========================================================
# TEMPERATURE / POWER
# =========================================================

st.subheader(
    "🌡️ Temperature"
)

st.line_chart(
    chart_df["temperature_c"],
    y_label="Temperature (°C)"
)


st.subheader(
    "⚡ Power Consumption"
)

st.line_chart(
    chart_df["power_kw"],
    y_label="Power (kW)"
)


# =========================================================
# RECENT DATA
# =========================================================

st.divider()

st.subheader(
    "🗃️ Recent Sensor Readings"
)


display_df = df.tail(10).copy()


display_df = display_df[
    [
        "timestamp",
        "pressure_bar",
        "flow_rate_lpm",
        "temperature_c",
        "power_kw",
        "energy_loss_percent",
        "status"
    ]
]


display_df.columns = [
    "Timestamp",
    "Pressure (bar)",
    "Air Flow (L/min)",
    "Temperature (°C)",
    "Power (kW)",
    "Energy Loss (%)",
    "Status"
]


st.dataframe(
    display_df.iloc[::-1],
    use_container_width=True,
    hide_index=True
)


# =========================================================
# SYSTEM ARCHITECTURE
# =========================================================

st.divider()

st.subheader(
    "🔗 Cloud System Architecture"
)

st.code(
    """
Synthetic Data
      ↓
MQTT Publisher
      ↓
HiveMQ Cloud
      ↓
Streamlit Cloud
      ↓
Live Monitoring Dashboard
      ↓
Energy Loss Detection
""",
    language="text"
)


st.caption(
    "Compressed Air Energy Loss Detection System | Cloud Dashboard"
)


# =========================================================
# AUTO REFRESH
# =========================================================

st.markdown(
    """
    <meta http-equiv="refresh" content="3">
    """,
    unsafe_allow_html=True
)