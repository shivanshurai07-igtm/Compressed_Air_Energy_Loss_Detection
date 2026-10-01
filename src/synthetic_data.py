import random
import time
import json
from datetime import datetime


def generate_data():

    pressure = round(random.uniform(6.5, 8.0), 2)
    flow_rate = round(random.uniform(80, 120), 2)
    temperature = round(random.uniform(25, 35), 2)
    power = round(random.uniform(2.0, 3.0), 2)

    # Simulate occasional compressed-air leakage
    if random.random() < 0.20:
        pressure = round(random.uniform(5.0, 6.4), 2)
        flow_rate = round(random.uniform(120, 180), 2)
        power = round(random.uniform(3.0, 4.5), 2)

    expected_flow = 100

    energy_loss = max(
        0,
        ((flow_rate - expected_flow) / expected_flow) * 100
    )

    energy_loss = round(min(energy_loss, 100), 2)

    if energy_loss >= 20:
        status = "HIGH LOSS"
    elif energy_loss >= 10:
        status = "WARNING"
    else:
        status = "NORMAL"

    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pressure_bar": pressure,
        "flow_rate_lpm": flow_rate,
        "temperature_c": temperature,
        "power_kw": power,
        "energy_loss_percent": energy_loss,
        "status": status
    }

    return data


if __name__ == "__main__":

    print("Compressed Air Energy Loss - Synthetic Data")
    print("-" * 55)

    while True:

        data = generate_data()

        print(json.dumps(data, indent=2))

        time.sleep(2)