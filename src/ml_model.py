import sqlite3
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib


DATABASE_NAME = "compressed_air.db"
MODEL_NAME = "energy_loss_model.pkl"


# --------------------------------------------------
# 1. Load data from SQLite
# --------------------------------------------------

connection = sqlite3.connect(DATABASE_NAME)

query = """
SELECT
    pressure_bar,
    flow_rate_lpm,
    temperature_c,
    power_kw,
    status
FROM air_data
"""

df = pd.read_sql_query(query, connection)

connection.close()


print("\nCompressed Air AI/ML Model")
print("-" * 50)

print("Total records:", len(df))


# --------------------------------------------------
# 2. Check data
# --------------------------------------------------

if len(df) < 30:
    print("\nNot enough data for training.")
    print("Let the MQTT system run for some time and collect more data.")
    exit()


print("\nClass distribution:")
print(df["status"].value_counts())


# --------------------------------------------------
# 3. Features and target
# --------------------------------------------------

features = [
    "pressure_bar",
    "flow_rate_lpm",
    "temperature_c",
    "power_kw"
]

X = df[features]
y = df["status"]


# --------------------------------------------------
# 4. Train/Test split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# --------------------------------------------------
# 5. Create Random Forest model
# --------------------------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)


# --------------------------------------------------
# 6. Train model
# --------------------------------------------------

print("\nTraining AI/ML model...")

model.fit(X_train, y_train)


# --------------------------------------------------
# 7. Test model
# --------------------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nModel Accuracy:")
print(f"{accuracy * 100:.2f}%")


print("\nClassification Report:")
print(classification_report(y_test, predictions))


# --------------------------------------------------
# 8. Save trained model
# --------------------------------------------------

joblib.dump(model, MODEL_NAME)

print("\nModel saved successfully!")
print("Model file:", MODEL_NAME)

print("-" * 50)
print("AI/ML training completed.")