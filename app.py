from flask import Flask, render_template, request, redirect, url_for
import folium
import os
from datetime import datetime, timedelta

app = Flask(__name__)
DATA_FILE = "rescue_data.txt"

SAFE_LOCATIONS = [
    {"name": "Salem Government Hospital", "lat": 11.6640, "lon": 78.1450},
    {"name": "Salem Collector Office Shelter", "lat": 11.6625, "lon": 78.1485},
    {"name": "Salem Corporation Community Hall", "lat": 11.6662, "lon": 78.1428}
]

TAMIL_KEYWORDS = {
    "ரத்தம்": "bleeding",
    "சிக்கி": "trapped",
    "காயம்": "injured",
    "குழந்தை": "child",
    "உதவி": "help",
    "வெள்ளம்": "flood"
}

def analyze_message(msg):
    detected = []

    for ta, en in TAMIL_KEYWORDS.items():
        if ta in msg:
            detected.append(en)

    return " ".join(detected) if detected else msg.lower()

def detect_priority(text):
    if any(w in text for w in ["bleeding", "trapped", "child"]):
        return "HIGH"

    elif any(w in text for w in ["injured", "flood"]):
        return "MEDIUM"

    return "LOW"

def ai_decision(priority):
    if priority == "HIGH":
        return "🚑 Dispatch Ambulance + Fire Rescue"

    elif priority == "MEDIUM":
        return "🏥 Send Medical Team"

    return "📞 Monitor & Call Victim"

def auto_escalation(time_str, priority, status):
    if priority != "HIGH" or status != "OPEN":
        return "NO"

    try:
        t = datetime.fromisoformat(time_str)

        if datetime.now() - t > timedelta(minutes=10):
            return "YES"

        return "NO"

    except:
        return "NO"

def time_ago(time_str):
    try:
        t = datetime.fromisoformat(time_str)
        diff = datetime.now() - t

        if diff.seconds < 60:
            return "Just now"

        if diff.seconds < 3600:
            return f"{diff.seconds // 60} minutes ago"

        return f"{diff.seconds // 3600} hours ago"

    except:
        return time_str

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/report", methods=["POST"])
def report():

    name = request.form["name"]
    msg = request.form["condition"]
    address = request.form["address"]
    lat = request.form["lat"]
    lon = request.form["lon"]

    analyzed = analyze_message(msg)
    priority = detect_priority(analyzed)
    decision = ai_decision(priority)

    lang = "TA" if any(k in msg for k in TAMIL_KEYWORDS) else "EN"

    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat()}|{name}|{msg}|{address}|{lang}|{priority}|{decision}|{lat},{lon}|OPEN\n"
        )

    return redirect(url_for("control"))

@app.route("/control")
def control():

    records = []
    high = 0
    medium = 0
    low = 0

    m = folium.Map(location=[11.6643, 78.1460], zoom_start=13)

    for place in SAFE_LOCATIONS:
        folium.Marker(
            [place["lat"], place["lon"]],
            tooltip=place["name"],
            icon=folium.Icon(color="green", icon="home")
        ).add_to(m)

    if os.path.exists(DATA_FILE):

        with open(DATA_FILE, "r", encoding="utf-8") as f:

            for line in f:

                parts = line.strip().split("|")

                if len(parts) != 9:
                    continue

                t, n, msg, address, lang, p, d, loc, s = parts

                lat, lon = loc.split(",")

                if p == "HIGH":
                    high += 1
                    color = "red"

                elif p == "MEDIUM":
                    medium += 1
                    color = "orange"

                else:
                    low += 1
                    color = "blue"

                folium.Marker(
                    [float(lat), float(lon)],
                    popup=f"<b>{n}</b><br>{address}<br>{msg}<br>Priority: {p}",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(m)

                records.append({
                    "name": n,
                    "msg": msg,
                    "address": address,
                    "lang": lang,
                    "priority": p,
                    "decision": d,
                    "time": time_ago(t),
                    "escalated": auto_escalation(t, p, s)
                })

    area_risk = "HIGH" if high >= 2 else "NORMAL"

    os.makedirs("static", exist_ok=True)
    m.save("static/map.html")

    return render_template(
        "control.html",
        records=records,
        high=high,
        medium=medium,
        low=low,
        area_risk=area_risk
    )

if __name__ == "__main__":
    app.run(debug=True)