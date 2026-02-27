from flask import Flask, render_template
from datetime import datetime
import random

app = Flask(__name__)

COIN_COUNT = 75


def generate_market():
    coins = []

    for i in range(1, COIN_COUNT + 1):
        symbol = f"COIN{i}"
        price = round(random.uniform(0.10, 5000), 2)

        scalp = random.choice(["BUY", "SELL", "HOLD"])
        swing = random.choice(["BUY", "SELL", "HOLD"])
        position = random.choice(["BUY", "SELL", "HOLD"])

        alignment = (
            (1 if scalp == "BUY" else -1 if scalp == "SELL" else 0)
            + (1 if swing == "BUY" else -1 if swing == "SELL" else 0)
            + (1 if position == "BUY" else -1 if position == "SELL" else 0)
        )

        coins.append({
            "symbol": symbol,
            "price": price,
            "scalp": scalp,
            "swing": swing,
            "position": position,
            "alignment": alignment
        })

    coins = sorted(coins, key=lambda x: x["alignment"], reverse=True)

    return coins


@app.route("/")
def home():
    results = generate_market()
    top = results[:10]

    return render_template(
        "index.html",
        top=top,
        results=results,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)