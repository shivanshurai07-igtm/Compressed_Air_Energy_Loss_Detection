import sqlite3

DATABASE_NAME = "compressed_air.db"


def create_database():

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS air_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pressure_bar REAL,
            flow_rate_lpm REAL,
            temperature_c REAL,
            power_kw REAL,
            energy_loss_percent REAL,
            status TEXT
        )
    """)

    connection.commit()
    connection.close()

    print("SQLite database and table created successfully!")


def save_data(data):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO air_data (
            timestamp,
            pressure_bar,
            flow_rate_lpm,
            temperature_c,
            power_kw,
            energy_loss_percent,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("timestamp"),
        data.get("pressure_bar"),
        data.get("flow_rate_lpm"),
        data.get("temperature_c"),
        data.get("power_kw"),
        data.get("energy_loss_percent"),
        data.get("status")
    ))

    connection.commit()
    connection.close()

    print("Data saved to SQLite!")


if __name__ == "__main__":
    create_database()