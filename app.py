import os
import time
import uuid
import pickle
import random
from datetime import datetime

STATE_FILE = "bots_state.pkl"


# ============================================
# BASE BOT (Each bot learns independently)
# ============================================
class BaseBot:
    def __init__(self, strategy_type, capital=1000):
        self.id = str(uuid.uuid4())
        self.strategy_type = strategy_type
        self.capital = capital
        self.pnl = 0
        self.trade_history = []
        self.learning_memory = []
        self.created_at = datetime.utcnow()

    def trade(self, market_data):
        """
        Replace this logic with your real strategy.
        Each strategy type behaves differently.
        """

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
        self.learn(result)

    def learn(self, trade_result):
        """
        Independent learning memory per bot
        """
        self.learning_memory.append({
            "result": trade_result,
            "timestamp": datetime.utcnow()
        })

        # Example adaptation logic
        if len(self.trade_history) > 10:
            avg = sum(self.trade_history[-10:]) / 10
            if avg < 0:
                self.capital *= 0.98  # risk reduction
            else:
                self.capital *= 1.01  # confidence boost


# ============================================
# BOT MANAGER (Never replaces bots)
# ============================================
class BotManager:
    def __init__(self):
        self.bots = []
        self.load_state()

    # --------- ADD BOTS (never replaces) ---------
    def add_bot(self, strategy_type, capital=1000):
        bot = BaseBot(strategy_type, capital)
        self.bots.append(bot)
        print(f"Added {strategy_type} bot | ID: {bot.id}")
        self.save_state()

    # --------- SAVE STATE ---------
    def save_state(self):
        with open(STATE_FILE, "wb") as f:
            pickle.dump(self.bots, f)

    # --------- LOAD STATE ---------
    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                self.bots = pickle.load(f)
            print(f"Loaded {len(self.bots)} bots from disk.")
        else:
            print("No previous state found. Starting fresh.")

    # --------- RUN ALL BOTS ---------
    def run_all(self, market_data):
        for bot in self.bots:
            bot.trade(market_data)
        self.save_state()

    # --------- STATUS ---------
    def status(self):
        for bot in self.bots:
            print(
                f"ID: {bot.id[:6]} | "
                f"Strategy: {bot.strategy_type} | "
                f"Capital: {round(bot.capital,2)} | "
                f"PnL: {round(bot.pnl,2)}"
            )


# ============================================
# MAIN LOOP (Keeps them UP)
# ============================================
if __name__ == "__main__":

    manager = BotManager()

    # Example: Only add if you WANT new ones
    if len(manager.bots) == 0:
        manager.add_bot("balanced", 1000)
        manager.add_bot("aggressive", 1000)
        manager.add_bot("scalper", 1000)

    while True:
        try:
            fake_market_data = {}
            manager.run_all(fake_market_data)
            manager.status()
            time.sleep(5)

        except Exception as e:
            print("Error occurred:", e)
            print("Restarting loop...")
            time.sleep(5)