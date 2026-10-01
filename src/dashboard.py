import streamlit as st
import sqlite3
import pandas as pd
import time

DATABASE_NAME = "compressed_air.db"

st.set_page_config(
    page_title="Compressed Air Energy Monitoring",
    page_icon="💨",
    layout="wide"
)


def get_data():

    connection = sqlite3.connect(DATABASE_NAME)

    query = """
    SELECT
        id,
        timestamp,
        pressure_bar,
        flow_rate_lpm,
        temperature_c,
        power_kw,
        energy_loss_percent,
        status
    FROM air_data
    ORDER BY id DESC
    """

    df = pd.read_sql_query(query, connection)

    connection.close()

    return df


# -------------------- HEADER --------------------

st.title("💨 Compressed Air Energy Monitoring System")

st.caption(
    "Real-time monitoring using MQTT, HiveMQ Cloud and SQLite Database"
)

st.divider()


# -------------------- DATABASE DATA --------------------

df = get_data()


if df.empty:

    st.warning("No data available in SQLite database.")

    st.stop()


latest = df.iloc[0]

pressure = latest["pressure_bar"]
flow = latest["flow_rate_lpm"]
energy_loss = latest["energy_loss_percent"]
status = latest["status"]
timestamp = latest["timestamp"]


# -------------------- STATUS --------------------

if status == "HIGH LOSS":

    st.error("🚨 HIGH ENERGY LOSS DETECTED")

elif status == "WARNING":

    st.warning("⚠️ ENERGY LOSS WARNING")

else:

    st.success("✅ SYSTEM NORMAL")


# -------------------- METRICS --------------------

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
        "Stored Readings",
        len(df)
    )


st.divider()


# -------------------- LAST UPDATE --------------------

st.write(f"🕒 **Last Reading:** {timestamp}")

st.divider()


# -------------------- GRAPHS --------------------

st.subheader("📊 Energy Loss")

graph_df = df.copy()

graph_df["timestamp"] = pd.to_datetime(
    graph_df["timestamp"]
)

graph_df = graph_df.sort_values("timestamp")

graph_df = graph_df.set_index("timestamp")


st.line_chart(
    graph_df["energy_loss_percent"],
    y_label="Energy Loss (%)"
)


st.subheader("💨 Pressure")

st.line_chart(
    graph_df["pressure_bar"],
    y_label="Pressure (bar)"
)


st.subheader("🌊 Air Flow")

st.line_chart(
    graph_df["flow_rate_lpm"],
    y_label="Air Flow (L/min)"
)


# -------------------- RECENT DATA --------------------

st.divider()

st.subheader("🗃️ Recent Sensor Readings")

display_df = df.head(10)[
    [
        "timestamp",
        "pressure_bar",
        "flow_rate_lpm",
        "energy_loss_percent",
        "status"
    ]
]

display_df.columns = [
    "Timestamp",
    "Pressure (bar)",
    "Air Flow (L/min)",
    "Energy Loss (%)",
    "Status"
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# -------------------- SYSTEM FLOW --------------------

st.divider()

st.subheader("🔗 System Architecture")

st.write(
    "Synthetic Data → MQTT → HiveMQ Cloud → "
    "MQTT Subscriber → SQLite → Dashboard"
)


st.caption(
    "Compressed Air Energy Loss Detection System | Layer 3"
)


# -------------------- AUTO REFRESH --------------------

time.sleep(2)

st.rerun()