const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

const pairs = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"];

function calculateRSI(closes, period = 14) {
  let gains = 0;
  let losses = 0;

  for (let i = 1; i < closes.length; i++) {
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

app.get("/", async (req, res) => {
  try {
    let results = [];

    for (let pair of pairs) {
      const tickerRes = await axios.get(
        `https://api.kraken.com/0/public/Ticker?pair=${pair}`
      );

      const ohlcRes = await axios.get(
        `https://api.kraken.com/0/public/OHLC?pair=${pair}&interval=60`
      );

      const tickerKey = Object.keys(tickerRes.data.result)[0];
      const ticker = tickerRes.data.result[tickerKey];

      const ohlcKey = Object.keys(ohlcRes.data.result)[0];
      const candles = ohlcRes.data.result[ohlcKey].slice(-15);

      const closes = candles.map(c => parseFloat(c[4]));

      const price = parseFloat(ticker.c[0]);
      const change24h = parseFloat(ticker.p[1]);
      const volatility = Math.abs(closes[closes.length - 1] - closes[0]);

      const rsi = calculateRSI(closes);

      let score = 0;

      if (rsi < 35) score += 3;
      if (change24h > 0) score += 2;
      if (volatility > 1) score += 1;

      let action = "HOLD";
      if (score >= 5) action = "BUY";
      if (rsi > 70) action = "SELL";

      results.push({
        pair,
        price,
        rsi: rsi.toFixed(2),
        change24h: change24h.toFixed(2),
        volatility: volatility.toFixed(2),
        score,
        action
      });
    }

    results.sort((a, b) => b.score - a.score);
    const best = results[0];

    const color =
      best.action === "BUY"
        ? "#00ff99"
        : best.action === "SELL"
        ? "#ff4d4d"
        : "#facc15";

    const confidence = Math.min(100, best.score * 20);

    res.send(`
      <html>
      <head>
        <meta http-equiv="refresh" content="30">
        <title>Structured Alpha Engine</title>
      </head>
      <body style="background:#0f172a; font-family:sans-serif; color:white; display:flex; justify-content:center; align-items:center; height:100vh;">
        <div style="background:#1e293b; padding:40px; border-radius:16px; width:350px; text-align:center; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
          <h1>Structured Alpha Engine</h1>
          <h2 style="color:${color};">${best.action}</h2>
          <h3>${best.pair}</h3>
          <p>Price: $${best.price}</p>
          <p>RSI: ${best.rsi}</p>
          <p>24h Change: ${best.change24h}%</p>
          <p>Volatility: ${best.volatility}</p>
          <p>Score: ${best.score}</p>
          <p>Confidence: ${confidence}%</p>
          <p style="margin-top:20px; font-size:12px; opacity:0.6;">
            Updated: ${new Date().toLocaleTimeString()}
          </p>
        </div>
      </body>
      </html>
    `);

  } catch (error) {
    res.send("Engine Error: " + error.message);
  }
});

app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});