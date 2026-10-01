import json
import ssl
import os

import joblib
import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

INPUT_TOPIC = "compressed_air/data"
OUTPUT_TOPIC = "compressed_air/ml_prediction"

MODEL_FILE = "energy_loss_model.pkl"


# ==========================================
# CHECK CREDENTIALS
# ==========================================

if not MQTT_BROKER:
    raise ValueError("MQTT_BROKER is missing in .env")

if not MQTT_USERNAME:
    raise ValueError("MQTT_USERNAME is missing in .env")

if not MQTT_PASSWORD:
    raise ValueError("MQTT_PASSWORD is missing in .env")


# ==========================================
# LOAD AI/ML MODEL
# ==========================================

print("Loading AI/ML model...")

model = joblib.load(MODEL_FILE)

print("AI/ML model loaded successfully!")
print("-" * 60)


# ==========================================
# RECEIVE DATA
# ==========================================

def on_message(client, userdata, message):

    try:

        data = json.loads(
            message.payload.decode()
        )


        # ==================================
        # PREPARE FEATURES
        # ==================================

        features = pd.DataFrame([{

            "pressure_bar":
                data["pressure_bar"],

            "flow_rate_lpm":
                data["flow_rate_lpm"],

            "temperature_c":
                data["temperature_c"],

            "power_kw":
                data["power_kw"]

        }])


        # ==================================
        # AI PREDICTION
        # ==================================

        prediction = model.predict(
            features
        )[0]


        probabilities = model.predict_proba(
            features
        )[0]


        confidence = max(
            probabilities
        ) * 100


        confidence = round(
            confidence,
            2
        )


        # ==================================
        # LEAKAGE RISK
        # ==================================

        if prediction == "HIGH LOSS":

            leakage_risk = "HIGH"

        elif prediction == "WARNING":

            leakage_risk = "MEDIUM"

        else:

            leakage_risk = "LOW"


        # ==================================
        # RESULT
        # ==================================

        result = {

            "timestamp":
                data["timestamp"],

            "prediction":
                prediction,

            "confidence_percent":
                confidence,

            "leakage_risk":
                leakage_risk,

            "pressure_bar":
                data["pressure_bar"],

            "flow_rate_lpm":
                data["flow_rate_lpm"],

            "temperature_c":
                data["temperature_c"],

            "power_kw":
                data["power_kw"]

        }


        # ==================================
        # PUBLISH ML RESULT
        # ==================================

        publish_result = client.publish(

            OUTPUT_TOPIC,

            json.dumps(result)

        )


        # ==================================
        # TERMINAL OUTPUT
        # ==================================

        print()

        print("AI/ML PREDICTION")

        print("-" * 45)

        print(
            "Prediction      :",
            prediction
        )

        print(
            "Confidence      :",
            f"{confidence}%"
        )

        print(
            "Leakage Risk    :",
            leakage_risk
        )

        print(
            "Pressure        :",
            data["pressure_bar"],
            "bar"
        )

        print(
            "Air Flow        :",
            data["flow_rate_lpm"],
            "L/min"
        )

        print(
            "Temperature     :",
            data["temperature_c"],
            "°C"
        )

        print(
            "Power           :",
            data["power_kw"],
            "kW"
        )

        print("-" * 45)


    except Exception as e:

        print(
            "Prediction error:",
            e
        )


# ==========================================
# MQTT CLIENT
# ==========================================

client = mqtt.Client(

    mqtt.CallbackAPIVersion.VERSION2,

    client_id=
        "compressed-air-ml-predictor"

)


client.username_pw_set(

    MQTT_USERNAME,

    MQTT_PASSWORD

)


# ==========================================
# TLS
# ==========================================

client.tls_set(

    cert_reqs=ssl.CERT_REQUIRED,

    tls_version=
        ssl.PROTOCOL_TLS_CLIENT

)


client.on_message = on_message


# ==========================================
# CONNECT
# ==========================================

print(
    "Connecting to HiveMQ Cloud..."
)

client.connect(

    MQTT_BROKER,

    MQTT_PORT,

    keepalive=60

)


print(
    "Connected to HiveMQ Cloud!"
)


# ==========================================
# SUBSCRIBE
# ==========================================

client.subscribe(
    INPUT_TOPIC
)


print(
    "Subscribed to:",
    INPUT_TOPIC
)


print(
    "AI/ML predictor is running..."
)


print("-" * 60)


# ==========================================
# KEEP RUNNING
# ==========================================

client.loop_forever()