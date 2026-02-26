const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

// Helper: Calculate RSI
function calculateRSI(closes, period = 14) {
  if (closes.length < period + 1) return null;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;

  if (avgLoss === 0) return 100;

  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

app.get("/", (req, res) => {
  res.send("Structured Alpha Engine Running");
});

app.get("/signals", async (req, res) => {
  try {
    const pairs = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"];
    let results = [];

    for (let pair of pairs) {
      // Get ticker
      const tickerRes = await axios.get(
        `https://api.kraken.com/0/public/Ticker?pair=${pair}`
      );

      const key = Object.keys(tickerRes.data.result)[0];
      const ticker = tickerRes.data.result[key];

      const price = parseFloat(ticker.c[0]);
      const volume = parseFloat(ticker.v[1]);
      const change24h =
        ((parseFloat(ticker.c[0]) - parseFloat(ticker.o)) /
          parseFloat(ticker.o)) *
        100;

      // Get 1h candles for RSI
      const ohlcRes = await axios.get(
        `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=60`
      );

      const ohlcKey = Object.keys(ohlcRes.data.result)[0];
      const candles = ohlcRes.data.result[ohlcKey];

      const closes = candles.slice(-15).map(c => parseFloat(c[4]));
      const rsi = calculateRSI(closes);

      // Volatility (last 14 candles range average)
      let volatility = 0;
      const recent = candles.slice(-14);
      for (let c of recent) {
        volatility += Math.abs(parseFloat(c[2]) - parseFloat(c[3]));
      }
      volatility = volatility / 14;

      // --- SCORING SYSTEM ---
      let score = 0;

      // RSI scoring
      if (rsi !== null) {
        if (rsi < 30) score += 4;      // Oversold = strong buy zone
        else if (rsi < 40) score += 2;
        else if (rsi > 70) score -= 2; // Overbought penalty
      }

      // 24h momentum
      if (change24h > 3) score += 3;
      else if (change24h > 1) score += 1;
      else if (change24h < -3) score -= 2;

      // Volume strength
      if (volume > 1000000) score += 2;

      // Volatility bonus
      if (volatility > price * 0.01) score += 2;

      let action = "HOLD";
      if (score >= 6) action = "BUY";
      if (score <= -3) action = "AVOID";

      results.push({
        pair,
        price,
        rsi: rsi ? rsi.toFixed(2) : null,
        change24h: change24h.toFixed(2),
        volatility: volatility.toFixed(2),
        score,
        action
      });
    }

    results.sort((a, b) => b.score - a.score);

    res.json({
      timestamp: new Date(),
      best_trade: results[0],
      all_pairs: results
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});