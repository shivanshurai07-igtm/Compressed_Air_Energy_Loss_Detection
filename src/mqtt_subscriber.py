import json
import ssl
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from database import save_data


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

MQTT_TOPIC = "compressed_air/data"


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
# MESSAGE CALLBACK
# ==========================================

def on_message(client, userdata, message):

    try:

        data = json.loads(
            message.payload.decode()
        )

        print("\nReceived from HiveMQ Cloud:")
        print(json.dumps(data, indent=2))

        save_data(data)

        print("Data saved to SQLite!")

        print("-" * 60)

    except Exception as e:

        print("Message error:", e)


# ==========================================
# MQTT CLIENT
# ==========================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="compressed-air-subscriber"
)

client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# ==========================================
# TLS SECURITY
# ==========================================

client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


client.on_message = on_message


# ==========================================
# CONNECT
# ==========================================

print("Connecting to HiveMQ Cloud...")

client.connect(
    MQTT_BROKER,
    MQTT_PORT,
    keepalive=60
)

print("Connected to HiveMQ Cloud!")


# ==========================================
# SUBSCRIBE
# ==========================================

client.subscribe(MQTT_TOPIC)

print("Subscribed to:", MQTT_TOPIC)

print("Waiting for data...")

print("-" * 60)


# ==========================================
# KEEP RUNNING
# ==========================================

client.loop_forever()