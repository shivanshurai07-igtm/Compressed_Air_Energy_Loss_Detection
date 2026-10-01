import json
import time
import ssl
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from synthetic_data import generate_data


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
# MQTT CLIENT
# ==========================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="compressed-air-publisher"
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

client.loop_start()


# ==========================================
# PUBLISH DATA
# ==========================================

try:

    while True:

        data = generate_data()

        message = json.dumps(data)

        result = client.publish(
            MQTT_TOPIC,
            message
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:

            print("\nPublished:")
            print(message)
            print("-" * 60)

        else:

            print("Publish failed!")

        time.sleep(2)


except KeyboardInterrupt:

    print("\nPublisher stopped.")


finally:

    client.loop_stop()

    client.disconnect()

    print("Disconnected from HiveMQ Cloud.")