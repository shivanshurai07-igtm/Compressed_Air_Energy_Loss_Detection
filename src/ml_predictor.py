import json
import ssl
import os
import time

import joblib
import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# MQTT CONFIGURATION
# =========================================================

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

INPUT_TOPIC = "compressed_air/data"
OUTPUT_TOPIC = "compressed_air/ml_prediction"


# =========================================================
# MODEL
# =========================================================

MODEL_PATH = "energy_loss_model.pkl"

model = joblib.load(MODEL_PATH)

print("AI model loaded successfully.")


# =========================================================
# CHECK MQTT CREDENTIALS
# =========================================================

if not MQTT_BROKER:
    raise ValueError("MQTT_BROKER missing in .env")

if not MQTT_USERNAME:
    raise ValueError("MQTT_USERNAME missing in .env")

if not MQTT_PASSWORD:
    raise ValueError("MQTT_PASSWORD missing in .env")


# =========================================================
# MQTT CONNECT
# =========================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties=None
):

    if reason_code == 0:

        print("Connected to HiveMQ Cloud")

        client.subscribe(
            INPUT_TOPIC,
            qos=1
        )

        print(
            "Subscribed to:",
            INPUT_TOPIC
        )

    else:

        print(
            "MQTT connection failed:",
            reason_code
        )


# =========================================================
# MQTT DISCONNECT
# =========================================================

def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties=None
):

    print(
        "MQTT disconnected:",
        reason_code
    )


# =========================================================
# MESSAGE RECEIVED
# =========================================================

def on_message(
    client,
    userdata,
    message
):

    try:

        # -------------------------------------------------
        # Decode MQTT message
        # -------------------------------------------------

        data = json.loads(
            message.payload.decode("utf-8")
        )

        print("\nSensor data received:")
        print(json.dumps(data, indent=2))


        # -------------------------------------------------
        # Prepare ML input
        # -------------------------------------------------

        features = pd.DataFrame([{
            "pressure_bar": float(
                data["pressure_bar"]
            ),

            "flow_rate_lpm": float(
                data["flow_rate_lpm"]
            ),

            "temperature_c": float(
                data["temperature_c"]
            ),

            "power_kw": float(
                data["power_kw"]
            )
        }])


        # -------------------------------------------------
        # AI Prediction
        # -------------------------------------------------

        prediction = model.predict(
            features
        )[0]


        # -------------------------------------------------
        # Confidence
        # -------------------------------------------------

        if hasattr(model, "predict_proba"):

            probabilities = model.predict_proba(
                features
            )[0]

            confidence = float(
                max(probabilities) * 100
            )

        else:

            confidence = 0.0


        confidence = round(
            confidence,
            2
        )


        # -------------------------------------------------
        # Leakage Risk
        # -------------------------------------------------

        if prediction == "HIGH LOSS":

            leakage_risk = "HIGH"

        elif prediction == "WARNING":

            leakage_risk = "MEDIUM"

        else:

            leakage_risk = "LOW"


        # -------------------------------------------------
        # AI RESULT
        # -------------------------------------------------

        result = {

            "timestamp": data.get(
                "timestamp"
            ),

            "prediction": str(
                prediction
            ),

            "confidence_percent": confidence,

            "leakage_risk": leakage_risk,

            "pressure_bar": data.get(
                "pressure_bar"
            ),

            "flow_rate_lpm": data.get(
                "flow_rate_lpm"
            ),

            "temperature_c": data.get(
                "temperature_c"
            ),

            "power_kw": data.get(
                "power_kw"
            ),

            "energy_loss_percent": data.get(
                "energy_loss_percent"
            )
        }


        # -------------------------------------------------
        # Publish AI Prediction
        # -------------------------------------------------

        result_json = json.dumps(
            result
        )

        client.publish(
            OUTPUT_TOPIC,
            result_json,
            qos=1,
            retain=True
        )


        # -------------------------------------------------
        # Console Output
        # -------------------------------------------------

        print("\n==============================")
        print("AI PREDICTION")
        print("==============================")

        print(
            "Prediction:",
            prediction
        )

        print(
            "Confidence:",
            f"{confidence}%"
        )

        print(
            "Leakage Risk:",
            leakage_risk
        )

        print(
            "Published to:",
            OUTPUT_TOPIC
        )

        print("==============================\n")


    except Exception as e:

        print(
            "AI prediction error:",
            e
        )


# =========================================================
# MQTT CLIENT
# =========================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="compressed-air-ai-predictor"
)


# =========================================================
# LOGIN
# =========================================================

client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# =========================================================
# TLS
# =========================================================

client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


# =========================================================
# RECONNECT SETTINGS
# =========================================================

client.reconnect_delay_set(
    min_delay=1,
    max_delay=30
)


# =========================================================
# CALLBACKS
# =========================================================

client.on_connect = on_connect

client.on_disconnect = on_disconnect

client.on_message = on_message


# =========================================================
# CONNECT
# =========================================================

print("Connecting to HiveMQ Cloud...")

client.connect(
    MQTT_BROKER,
    MQTT_PORT,
    keepalive=60
)


# =========================================================
# START LOOP
# =========================================================

print("AI Prediction service started.")

client.loop_forever()