const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

const BASE_URL = "https://api.kraken.com";

// ---------- Coin Mapping ----------
const COIN_INFO = {
  XRPUSD: { name: "Ripple", symbol: "XRP" },
  SOLUSD: { name: "Solana", symbol: "SOL" },
  SHIBUSD: { name: "Shiba Inu", symbol: "SHIB" },
  PEPEUSD: { name: "Pepe", symbol: "PEPE" },
  XBTUSD: { name: "Bitcoin", symbol: "BTC" },
  ETHUSD: { name: "Ethereum", symbol: "ETH" }
};

const SCAN_PAIRS = Object.keys(COIN_INFO);

// ---------- Fetch Ticker ----------
async function getTicker(pair) {
  const response = await axios.get(
    `${BASE_URL}/0/public/Ticker?pair=${pair}`
  );

  const key = Object.keys(response.data.result)[0];
  return response.data.result[key];
}

// ---------- Scoring Engine ----------
function scoreAsset(price, volume24h, change24h) {
  let score = 0;

  // Volume strength
  if (volume24h > 1_000_000) score += 2;
  if (volume24h > 10_000_000) score += 2;

  // Momentum
  if (change24h > 0) score += 1;
  if (change24h > 2) score += 2;
  if (change24h > 5) score += 3;

  // Price tiers
  if (price > 1) score += 1;
  if (price > 10) score += 1;

  return score;
}

// ---------- Routes ----------
app.get("/", (req, res) => {
  res.send("Structured Alpha Public Market Scanner Running");
});

app.get("/signals", async (req, res) => {
  try {
    const results = [];

    for (let pair of SCAN_PAIRS) {
      try {
        const ticker = await getTicker(pair);

        const price = parseFloat(ticker.c[0]);
        const volume = parseFloat(ticker.v[1]);
        const open24h = parseFloat(ticker.o);
        const change24h = ((price - open24h) / open24h) * 100;

        const score = scoreAsset(price, volume, change24h);

        let action = "HOLD";
        if (score >= 8) action = "STRONG BUY";
        else if (score >= 5) action = "BUY";
        else if (score <= 2) action = "SELL";

        results.push({
          coin_name: COIN_INFO[pair].name,
          symbol: COIN_INFO[pair].symbol,
          pair,
          price,
          change_24h_percent: change24h.toFixed(2) + "%",
          volume_24h: volume,
          score,
          action
        });

      } catch (err) {
        // Skip invalid pairs
      }
    }

    results.sort((a, b) => b.score - a.score);

    res.json({
      timestamp: new Date(),
      ranked_opportunities: results
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});