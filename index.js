const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;
const BASE_URL = "https://api.kraken.com";

// ------------------ RSI CALCULATION ------------------
function calculateRSI(closes, period = 14) {
  if (closes.length <= period) return null;

  let gains = 0;
  let losses = 0;

  for (let i = closes.length - period; i < closes.length; i++) {
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

// ------------------ SCORING SYSTEM ------------------
function scoreAsset(data) {
  let score = 0;

  const change = parseFloat(data.change_24h_percent);
  const volume = parseFloat(data.volume_24h);
  const rsi = data.rsi;

  // Volume strength
  if (volume > 10000000) score += 2;
  if (volume > 50000000) score += 2;

  // Momentum
  if (change > 0) score += 2;
  if (change > 3) score += 2;
  if (change < -3) score -= 2;

  // RSI logic
  if (rsi && rsi < 35) score += 2; // oversold bounce
  if (rsi && rsi > 70) score -= 2; // overbought

  return score;
}

// ------------------ FETCH ALL USD PAIRS ------------------
async function getUSDPairs() {
  const response = await axios.get(`${BASE_URL}/0/public/AssetPairs`);
  const pairs = response.data.result;

  return Object.keys(pairs).filter(pair =>
    pairs[pair].quote === "ZUSD"
  );
}

// ------------------ FETCH TICKER ------------------
async function getTicker(pair) {
  const response = await axios.get(
    `${BASE_URL}/0/public/Ticker?pair=${pair}`
  );
  const key = Object.keys(response.data.result)[0];
  const ticker = response.data.result[key];

  return {
    price: parseFloat(ticker.c[0]),
    volume_24h: parseFloat(ticker.v[1]),
    change_24h_percent:
      ((parseFloat(ticker.c[0]) - parseFloat(ticker.o)) /
        parseFloat(ticker.o)) *
      100
  };
}

// ------------------ FETCH CANDLES ------------------
async function getCandles(pair) {
  const response = await axios.get(
    `${BASE_URL}/0/public/OHLC?pair=${pair}&interval=60`
  );

  const key = Object.keys(response.data.result)[0];
  const candles = response.data.result[key];

  return candles.map(c => parseFloat(c[4])); // close prices
}

// ------------------ MAIN ROUTE ------------------
app.get("/", (req, res) => {
  res.send("Structured Alpha Market Engine Running");
});

app.get("/scan", async (req, res) => {
  try {
    const pairs = await getUSDPairs();
    const results = [];

    for (let pair of pairs.slice(0, 40)) { // limit to 40 for speed
      try {
        const ticker = await getTicker(pair);
        const closes = await getCandles(pair);
        const rsi = calculateRSI(closes);

        const data = {
          pair,
          price: ticker.price,
          volume_24h: ticker.volume_24h,
          change_24h_percent: ticker.change_24h_percent.toFixed(2),
          rsi: rsi ? rsi.toFixed(2) : null
        };

        const score = scoreAsset(data);

        let action = "HOLD";
        if (score >= 6) action = "BUY";
        if (score <= 1) action = "SELL";

        results.push({ ...data, score, action });
      } catch (e) {
        continue;
      }
    }

    results.sort((a, b) => b.score - a.score);

    res.json({
      timestamp: new Date(),
      top_opportunities: results.slice(0, 10),
      market_overview: results
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});