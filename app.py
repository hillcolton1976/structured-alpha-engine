from flask import Flask, render_template_string
import ccxt
import pandas as pd

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

TIMEFRAME = '1m'
CANDLE_LIMIT = 50
START_BALANCE = 50.0
MAX_POSITIONS = 7
POSITION_SIZE = 0.15  # 15%

SYMBOLS = [
'BTC/USDT','ETH/USDT','XRP/USDT','BNB/USDT','SOL/USDT',
'ADA/USDT','DOGE/USDT','AVAX/USDT','LINK/USDT','DOT/USDT',
'MATIC/USDT','LTC/USDT','BCH/USDT','UNI/USDT','ATOM/USDT',
'ICP/USDT','APT/USDT','NEAR/USDT','ARB/USDT','OP/USDT'
]

exchange = ccxt.coinbase()

# ==============================
# STATE
# ==============================

balance = START_BALANCE
positions = {}
total_trades = 0
wins = 0
losses = 0
last_action = "Starting..."
recent_signals = []

# ==============================
# DATA
# ==============================

def get_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
        if len(ohlcv) < 20:
            return None

        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
        df['ema5'] = df['close'].ewm(span=5).mean()
        df['ema13'] = df['close'].ewm(span=13).mean()
        return df
    except:
        return None

# ==============================
# STRATEGY
# ==============================

def momentum_entry(df):
    if df is None or len(df) < 20:
        return False
    return df['ema5'].iloc[-1] > df['ema13'].iloc[-1]

def momentum_exit(df):
    if df is None or len(df) < 20:
        return False
    return df['ema5'].iloc[-1] < df['ema13'].iloc[-1]

# ==============================
# ENGINE
# ==============================

def evaluate():
    global balance, positions, total_trades, wins, losses, last_action

    # EXIT LOGIC
    for symbol in list(positions.keys()):
        df = get_data(symbol)
        if df is None:
            continue

        current_price = df['close'].iloc[-1]
        entry_price = positions[symbol]['entry']

        if momentum_exit(df):
            pnl = (current_price - entry_price) / entry_price
            trade_value = positions[symbol]['size'] * current_price

            balance += trade_value
            total_trades += 1

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            last_action = f"Exited {symbol} ({round(pnl*100,2)}%)"
            recent_signals.insert(0, last_action)
            positions.pop(symbol)

    # ENTRY LOGIC
    for symbol in SYMBOLS:
        if len(positions) >= MAX_POSITIONS:
            break

        if symbol in positions:
            continue

        df = get_data(symbol)
        if df is None:
            continue

        if momentum_entry(df):
            allocation = balance * POSITION_SIZE
            if allocation <= 1:
                continue

            entry_price = df['close'].iloc[-1]
            size = allocation / entry_price

            balance -= allocation

            positions[symbol] = {
                "entry": entry_price,
                "size": size
            }

            last_action = f"Entered {symbol}"
            recent_signals.insert(0, last_action)

# ==============================
# DASHBOARD
# ==============================

@app.route("/")
def dashboard():
    evaluate()

    equity = balance
    for symbol, pos in positions.items():
        df = get_data(symbol)
        if df is None:
            continue
        current_price = df['close'].iloc[-1]
        equity += pos['size'] * current_price

    roi = ((equity - START_BALANCE) / START_BALANCE) * 100
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    # ROUND HERE (NOT IN TEMPLATE)
    equity_r = round(equity, 2)
    balance_r = round(balance, 2)
    roi_r = round(roi, 2)
    win_rate_r = round(win_rate, 2)

    return render_template_string("""
    <html>
    <head>
    <meta http-equiv="refresh" content="60">
    <style>
        body {
            background: linear-gradient(180deg,#0f172a,#1e293b);
            color: #e2e8f0;
            font-family: Arial;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        h1 { color: #60a5fa; }
        h2 { color: #a78bfa; }
    </style>
    </head>
    <body>
        <h1>🚀 Aggressive Momentum Engine</h1>

        <div class="card">
            <b>Equity:</b> ${{equity}}<br>
            <b>Cash:</b> ${{balance}}<br>
            <b>ROI:</b> {{roi}}%<br>
            <b>Last Action:</b> {{last_action}}
        </div>

        <div class="card">
            <h2>Performance</h2>
            Trades: {{total_trades}}<br>
            Wins: {{wins}}<br>
            Losses: {{losses}}<br>
            Win Rate: {{win_rate}}%
        </div>

        <div class="card">
            <h2>Open Positions ({{positions|length}} / """ + str(MAX_POSITIONS) + """)</h2>
            {% if positions %}
                {% for s,p in positions.items() %}
                    {{s}} — Entry: {{p.entry}}<br>
                {% endfor %}
            {% else %}
                No open positions
            {% endif %}
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {% for signal in recent_signals[:10] %}
                {{signal}}<br>
            {% endfor %}
        </div>

    </body>
    </html>
    """,
    equity=equity_r,
    balance=balance_r,
    roi=roi_r,
    win_rate=win_rate_r,
    last_action=last_action,
    total_trades=total_trades,
    wins=wins,
    losses=losses,
    positions=positions,
    recent_signals=recent_signals
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)