import os
import time
import uuid
import pickle
import random
import threading
from datetime import datetime
from flask import Flask, render_template

# ==============================
# Flask App
# ==============================

app = Flask(__name__)

STATE_FILE = "bots_state.pkl"

# ==============================
# Base Bot (Independent Learning)
# ==============================

class BaseBot:
    def __init__(self, strategy_type, capital=1000):
        self.id = str(uuid.uuid4())
        self.strategy_type = strategy_type
        self.capital = capital
        self.pnl = 0
        self.trade_history = []
        self.learning_memory = []
        self.created_at = datetime.utcnow()

    def trade(self):
        # Strategy behavior
        if self.strategy_type == "scalper":
            result = random.uniform(-2, 3)

        elif self.strategy_type == "aggressive":
            result = random.uniform(-10, 15)

        elif self.strategy_type == "balanced":
            result = random.uniform(-5, 7)

        else:
            result = random.uniform(-3, 3)

        self.pnl += result
        self.capital += result

        self.trade_history.append(result)
        self.learning_memory.append({
            "timestamp": datetime.utcnow(),
            "result": result
        })

    def to_dict(self):
        return {
            "id": self.id,
            "strategy": self.strategy_type,
            "capital": round(self.capital, 2),
            "pnl": round(self.pnl, 2),
            "trades": len(self.trade_history)
        }

# ==============================
# Bot Manager
# ==============================

class BotManager:
    def __init__(self):
        self.bots = []

    def add_bot(self, strategy):
        bot = BaseBot(strategy)
        self.bots.append(bot)
        self.save_state()

    def run_all(self):
        for bot in self.bots:
            bot.trade()
        self.save_state()

    def save_state(self):
        with open(STATE_FILE, "wb") as f:
            pickle.dump(self.bots, f)

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                self.bots = pickle.load(f)

manager = BotManager()
manager.load_state()

# ==============================
# Auto Create Bots If None Exist
# ==============================

if not manager.bots:
    manager.add_bot("scalper")
    manager.add_bot("aggressive")
    manager.add_bot("balanced")

# ==============================
# Background Trading Thread
# ==============================

def bot_loop():
    while True:
        manager.run_all()
        time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()

# ==============================
# Routes
# ==============================

@app.route("/")
def dashboard():
    bot_data = [bot.to_dict() for bot in manager.bots]
    total_equity = round(sum(bot.capital for bot in manager.bots), 2)
    return render_template(
        "dashboard.html",
        bots=bot_data,
        total_equity=total_equity
    )