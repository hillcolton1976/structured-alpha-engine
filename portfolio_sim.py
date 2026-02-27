import random

START_BALANCE = 50
TARGET_STAGE1 = 200
TARGET_STAGE2 = 1000
TOTAL_TRADES = 500

balance = START_BALANCE
peak = balance
max_drawdown = 0
wins = 0
losses = 0

def take_trade(balance, win_rate, risk_percent, rr_ratio):
    risk_amount = balance * risk_percent
    
    if random.random() < win_rate:
        return balance + (risk_amount * rr_ratio), True
    else:
        return balance - risk_amount, False

for trade in range(TOTAL_TRADES):

    if balance < TARGET_STAGE1:
        win_rate = 0.45
        risk_percent = 0.06
        rr_ratio = 2

    elif balance < TARGET_STAGE2:
        win_rate = 0.48
        risk_percent = 0.03
        rr_ratio = 1.8

    else:
        win_rate = 0.50
        risk_percent = 0.02
        rr_ratio = 1.5

    balance, won = take_trade(balance, win_rate, risk_percent, rr_ratio)

    if won:
        wins += 1
    else:
        losses += 1

    if balance > peak:
        peak = balance

    drawdown = (peak - balance) / peak
    if drawdown > max_drawdown:
        max_drawdown = drawdown

print("\n========== RESULTS ==========")
print("Starting Balance:", START_BALANCE)
print("Ending Balance:", round(balance, 2))
print("Wins:", wins)
print("Losses:", losses)
print("Win Rate:", round((wins / TOTAL_TRADES) * 100, 2), "%")
print("Max Drawdown:", round(max_drawdown * 100, 2), "%")

if balance >= TARGET_STAGE2:
    print("🔥 Reached $1,000 target.")
elif balance >= TARGET_STAGE1:
    print("⚡ Reached $200 target.")
else:
    print("❌ Did not reach $200.")