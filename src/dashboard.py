import streamlit as st
import paho.mqtt.client as mqtt
import json
import ssl
import threading
from collections import deque
import pandas as pd


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Compressed Air Energy Intelligence",
    page_icon="💨",
    layout="wide"
)


# =========================================================
# MQTT CONFIGURATION
# =========================================================

MQTT_TOPIC = "compressed_air/data"
ML_TOPIC = "compressed_air/ml_prediction"


# =========================================================
# MQTT CONNECTION
# =========================================================

@st.cache_resource
def start_mqtt():

    data_store = {
        "readings": deque(maxlen=100),
        "ml_prediction": None,
        "connected": False,
        "lock": threading.Lock()
    }

    # -----------------------------------------------------
    # MQTT CONNECT
    # -----------------------------------------------------

    def on_connect(
        client,
        userdata,
        flags,
        reason_code,
        properties=None
    ):

        if reason_code == 0:

            data_store["connected"] = True

            client.subscribe(MQTT_TOPIC)
            client.subscribe(ML_TOPIC)

            print("Connected to HiveMQ Cloud")
            print("Subscribed to:", MQTT_TOPIC)
            print("Subscribed to:", ML_TOPIC)

        else:

            data_store["connected"] = False

            print(
                "MQTT connection failed:",
                reason_code
            )

    # -----------------------------------------------------
    # MQTT DISCONNECT
    # -----------------------------------------------------

    def on_disconnect(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties=None
    ):

        data_store["connected"] = False

        print("Disconnected from HiveMQ Cloud")

    # -----------------------------------------------------
    # MQTT MESSAGE
    # -----------------------------------------------------

    def on_message(
        client,
        userdata,
        message
    ):

        try:

            payload = json.loads(
                message.payload.decode("utf-8")
            )

            with data_store["lock"]:

                # Normal sensor data
                if message.topic == MQTT_TOPIC:

                    data_store["readings"].append(
                        payload
                    )

                # AI / ML prediction
                elif message.topic == ML_TOPIC:

                    data_store["ml_prediction"] = payload

                    print(
                        "AI Prediction received:",
                        payload
                    )

        except Exception as e:

            print(
                "MQTT message error:",
                e
            )

    # -----------------------------------------------------
    # STREAMLIT SECRETS
    # -----------------------------------------------------

    broker = st.secrets["MQTT_BROKER"]

    port = int(
        st.secrets.get(
            "MQTT_PORT",
            8883
        )
    )

    username = st.secrets["MQTT_USERNAME"]

    password = st.secrets["MQTT_PASSWORD"]

    # -----------------------------------------------------
    # MQTT CLIENT
    # -----------------------------------------------------

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="cloud-compressed-air-dashboard"
    )

    client.username_pw_set(
        username,
        password
    )

    # -----------------------------------------------------
    # TLS
    # -----------------------------------------------------

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    # -----------------------------------------------------
    # CALLBACKS
    # -----------------------------------------------------

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # -----------------------------------------------------
    # CONNECT
    # -----------------------------------------------------

    try:

        client.connect(
            broker,
            port,
            keepalive=60
        )

        client.loop_start()

    except Exception as e:

        data_store["connected"] = False

        print(
            "MQTT connection error:",
            e
        )

    return data_store


# =========================================================
# START MQTT
# =========================================================

mqtt_data = start_mqtt()


# =========================================================
# HEADER
# =========================================================

st.html("""
<div style="
    width:100%;
    box-sizing:border-box;
    padding:24px 28px;
    border-radius:16px;
    background:linear-gradient(
        135deg,
        #102832 0%,
        #0b1c24 55%,
        #0b171d 100%
    );
    border:1px solid rgba(80,190,220,0.25);
    box-shadow:0 8px 25px rgba(0,0,0,0.20);
    margin-bottom:20px;
">

    <div style="
        color:white;
        font-size:26px;
        font-weight:700;
        letter-spacing:1px;
    ">
        💨 COMPRESSED AIR
        <span style="color:#43c4e5;">
            ENERGY INTELLIGENCE
        </span>
    </div>

    <div style="
        margin-top:7px;
        color:#9bb1ba;
        font-size:13px;
    ">
        Real-Time Energy Loss Monitoring & Detection
    </div>

</div>
""")


# =========================================================
# LIVE DASHBOARD
# =========================================================

@st.fragment(run_every="3s")
def live_dashboard():

    # -----------------------------------------------------
    # GET CURRENT READINGS
    # -----------------------------------------------------

    with mqtt_data["lock"]:

        readings = list(
            mqtt_data["readings"]
        )

        ml_prediction = mqtt_data["ml_prediction"]

    # -----------------------------------------------------
    # CONNECTION STATUS
    # -----------------------------------------------------

    if mqtt_data["connected"]:

        st.success(
            "🟢 SYSTEM ONLINE • MQTT CONNECTED • HiveMQ CLOUD"
        )

    else:

        st.error(
            "🔴 MQTT CONNECTION LOST"
        )

    # -----------------------------------------------------
    # WAITING FOR DATA
    # -----------------------------------------------------

    if len(readings) == 0:

        st.info(
            "🔄 Connected to HiveMQ Cloud. "
            "Waiting for sensor data..."
        )

        return

    # -----------------------------------------------------
    # DATAFRAME
    # -----------------------------------------------------

    df = pd.DataFrame(
        readings
    )

    # -----------------------------------------------------
    # REQUIRED COLUMNS
    # -----------------------------------------------------

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

            df[column] = 0

    # -----------------------------------------------------
    # TIMESTAMP
    # -----------------------------------------------------

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

    if df.empty:

        st.warning(
            "No valid sensor data received."
        )

        return

    # -----------------------------------------------------
    # LATEST READING
    # -----------------------------------------------------

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

    status = str(
        latest["status"]
    )

    timestamp = latest["timestamp"]

    # =====================================================
    # AI / ML PREDICTION
    # =====================================================

    st.divider()

    st.subheader(
        "🤖 AI / ML Analysis"
    )

    if ml_prediction:

        prediction = ml_prediction.get(
            "prediction",
            "N/A"
        )

        confidence = ml_prediction.get(
            "confidence_percent",
            0
        )

        leakage_risk = ml_prediction.get(
            "leakage_risk",
            "N/A"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "AI Prediction",
                str(prediction)
            )

        with col2:

            st.metric(
                "Confidence",
                f"{confidence}%"
            )

        with col3:

            st.metric(
                "Leakage Risk",
                str(leakage_risk)
            )

        # AI status message

        if prediction == "HIGH LOSS":

            st.error(
                "🚨 AI DETECTED HIGH ENERGY LOSS / "
                "POSSIBLE AIR LEAKAGE"
            )

        elif prediction == "WARNING":

            st.warning(
                "⚠️ AI DETECTED WARNING CONDITION"
            )

        elif prediction == "NORMAL":

            st.success(
                "✅ AI PREDICTION: SYSTEM NORMAL"
            )

    else:

        st.info(
            "🤖 Waiting for AI/ML prediction..."
        )

    # =====================================================
    # ALERT
    # =====================================================

    if status == "HIGH LOSS":

        st.error(
            "🚨 HIGH ENERGY LOSS DETECTED — "
            "POSSIBLE COMPRESSED AIR LEAKAGE"
        )

    elif status == "WARNING":

        st.warning(
            "⚠️ ENERGY LOSS WARNING"
        )

    else:

        st.success(
            "✅ SYSTEM NORMAL"
        )

    # =====================================================
    # LIVE SYSTEM PARAMETERS
    # =====================================================

    st.subheader(
        "📊 Live System Parameters"
    )

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
            "System Status",
            status
        )

    # =====================================================
    # MACHINE PARAMETERS
    # =====================================================

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
            "Power Consumption",
            f"{power:.2f} kW"
        )

    with col3:

        st.metric(
            "Live Readings",
            len(df)
        )

    # =====================================================
    # LAST UPDATE
    # =====================================================

    st.write(
        f"🕒 **Last Reading:** "
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.divider()

    # =====================================================
    # CHART DATA
    # =====================================================

    chart_df = df.set_index(
        "timestamp"
    )

    # =====================================================
    # ENERGY LOSS
    # =====================================================

    st.subheader(
        "📊 Energy Loss Trend"
    )

    st.line_chart(
        chart_df["energy_loss_percent"],
        y_label="Energy Loss (%)"
    )

    # =====================================================
    # PRESSURE
    # =====================================================

    st.subheader(
        "💨 Pressure Trend"
    )

    st.line_chart(
        chart_df["pressure_bar"],
        y_label="Pressure (bar)"
    )

    # =====================================================
    # AIR FLOW
    # =====================================================

    st.subheader(
        "🌊 Air Flow Trend"
    )

    st.line_chart(
        chart_df["flow_rate_lpm"],
        y_label="Air Flow (L/min)"
    )

    # =====================================================
    # TEMPERATURE
    # =====================================================

    st.subheader(
        "🌡️ Temperature Trend"
    )

    st.line_chart(
        chart_df["temperature_c"],
        y_label="Temperature (°C)"
    )

    # =====================================================
    # POWER
    # =====================================================

    st.subheader(
        "⚡ Power Consumption"
    )

    st.line_chart(
        chart_df["power_kw"],
        y_label="Power (kW)"
    )

    # =====================================================
    # RECENT READINGS
    # =====================================================

    st.divider()

    st.subheader(
        "🗃️ Recent Sensor Readings"
    )

    display_df = df.tail(
        10
    ).copy()

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

    # =====================================================
    # CLOUD ARCHITECTURE
    # =====================================================

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
      ├──────────────→ Node-RED
      │                   ↓
      │             Industrial Dashboard
      │
      └──────────────→ Streamlit Cloud
                          ↓
                    Cloud Dashboard
                          ↓
                    AI/ML Analysis
        """,
        language="text"
    )

    st.caption(
        "Compressed Air Energy Loss Detection System | Cloud Dashboard"
    )


# =========================================================
# RUN LIVE DASHBOARD
# =========================================================

live_dashboard()
