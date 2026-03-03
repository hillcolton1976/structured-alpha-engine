from flask import Flask
import requests
import os

app = Flask(__name__)

@app.route("/")
def home():
    try:
        r = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        return f"Status: {r.status_code}<br>Response: {r.text}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)