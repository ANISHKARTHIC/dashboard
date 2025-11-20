from collections import deque
from datetime import datetime
from flask import Flask, request, jsonify, render_template, make_response
import random

# Flask App
app = Flask(__name__, static_folder="static", template_folder="templates")

# Store latest 300 sensor samples
HISTORY_MAX = 300
history = deque(maxlen=HISTORY_MAX)
latest_sample = {}


# -------------------------------
# RISK CALCULATION ENGINE
# -------------------------------
def compute_risk(sample: dict) -> dict:
    """
    Computes cloudburst risk level from a sensor sample.
    Scoring:
        - Rainfall: >=30 → +3 | >=10 → +2 | >0 → +1
        - Humidity: >=90 → +2 | >=80 → +1
        - Soil moisture == 1 → +2
        - Ultrasonic: <30 → +3 | <60 → +1
    """
    score = 0

    rain = sample.get("rainfall", 0)
    hum = sample.get("humidity", 0)
    soil = sample.get("soil", 0)
    ult = sample.get("ultrasonic", 999)

    # Rainfall
    if rain >= 30:
        score += 3
    elif rain >= 10:
        score += 2
    elif rain > 0:
        score += 1

    # Humidity
    if hum >= 90:
        score += 2
    elif hum >= 80:
        score += 1

    # Soil
    if int(soil) == 1:
        score += 2

    # Ultrasonic
    if ult < 30:
        score += 3
    elif ult < 60:
        score += 1

    # Risk category
    if score >= 6:
        return {"score": score, "label": "High Cloudburst Risk", "key": "high"}
    elif score >= 3:
        return {"score": score, "label": "Moderate Risk", "key": "moderate"}
    else:
        return {"score": score, "label": "Low Risk", "key": "low"}


# -------------------------------
# CORS Response Helper
# -------------------------------
def make_cors_response(obj, status=200):
    """Create JSON response with CORS headers."""
    resp = make_response(jsonify(obj), status)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


# -------------------------------
# ROUTES
# -------------------------------
@app.route("/")
def index():
    """Serve Dashboard UI."""
    return render_template("index.html")


@app.route("/update", methods=["POST", "OPTIONS"])
def update():
    """Receive sensor data from ESP32 / simulation and store it."""

    if request.method == "OPTIONS":
        return make_cors_response({}, 204)

    data = request.get_json(force=True, silent=True)
    if not data:
        return make_cors_response({"error": "Invalid JSON"}, 400)

    # Validation and coercion
    try:
        temperature = float(data.get("temperature", 0))
        humidity = float(data.get("humidity", 0))
        rainfall = float(data.get("rainfall", 0))
        soil = int(data.get("soil", 0))
        ultrasonic = float(data.get("ultrasonic", 999))
    except Exception:
        return make_cors_response({"error": "Invalid data types"}, 400)

    timestamp = datetime.utcnow().isoformat() + "Z"

    # Prepare sample
    sample = {
        "temperature": round(temperature, 2),
        "humidity": round(humidity, 2),
        "rainfall": round(rainfall, 2),
        "soil": int(bool(soil)),
        "ultrasonic": round(ultrasonic, 2),
        "timestamp": timestamp,
    }

    # Risk evaluation
    sample["risk"] = compute_risk(sample)

    # Store sample
    history.append(sample)
    global latest_sample
    latest_sample = sample

    return make_cors_response({"status": "ok", "sample": sample}, 201)


@app.route("/data", methods=["GET"])
def data():
    """Return latest reading + history array."""
    return make_cors_response({
        "latest": latest_sample,
        "history": list(history)
    })


@app.route("/simulate", methods=["GET"])
def simulate():
    """
    Generate mock sensor values for demo/testing.
    Automatically inserts into /update route.
    """

    temp = round(random.uniform(12, 35), 2)
    hum = round(random.uniform(40, 98), 2)

    # 12% chance to trigger heavy rainfall zone
    rain = round(random.uniform(10, 50), 2) if random.random() < 0.12 else round(random.uniform(0, 8), 2)

    soil = 1 if random.random() < 0.45 else 0
    ult = round(random.uniform(8, 120), 2)

    payload = {
        "temperature": temp,
        "humidity": hum,
        "rainfall": rain,
        "soil": soil,
        "ultrasonic": ult
    }

    # Reuse the update logic
    with app.test_request_context('/update', method='POST', json=payload):
        update()

    return make_cors_response({"status": "simulated", "payload": payload})


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
