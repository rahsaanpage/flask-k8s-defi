from flask import Flask, render_template, jsonify
import os
import platform
import time

app = Flask(__name__)
start_time = time.time()

@app.route("/")
def hello():
    hostname = os.environ.get("HOSTNAME", "unknown")
    return render_template("index.html", hostname=hostname)

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "pod": os.environ.get("HOSTNAME", "unknown")})

@app.route("/api/info")
def info():
    uptime = int(time.time() - start_time)
    return jsonify({
        "hostname": os.environ.get("HOSTNAME", "unknown"),
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "uptime_seconds": uptime
    })

@app.route("/api/pod")
def pod():
    return jsonify({"pod": os.environ.get("HOSTNAME", "unknown")})

@app.route("/exchange")
def exchange():
    hostname = os.environ.get("HOSTNAME", "unknown")
    return render_template("exchange.html", hostname=hostname)

@app.route("/charts")
def charts():
    hostname = os.environ.get("HOSTNAME", "unknown")
    return render_template("charts.html", hostname=hostname)

@app.route("/pool")
def pool():
    hostname = os.environ.get("HOSTNAME", "unknown")
    return render_template("pool.html", hostname=hostname)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
