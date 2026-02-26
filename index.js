const express = require("express");
const axios = require("axios");
const crypto = require("crypto");
const qs = require("querystring");

const app = express();
const PORT = process.env.PORT || 8080;

const API_KEY = process.env.KRAKEN_API_KEY;
const API_SECRET = process.env.KRAKEN_API_SECRET;

const BASE_URL = "https://api.kraken.com";

// ---------- Utility: Kraken Signature ----------
function getKrakenSignature(path, request, secret, nonce) {
  const message = qs.stringify(request);
  const secret_buffer = Buffer.from(secret, "base64");
  const hash = crypto
    .createHash("sha256")
    .update(nonce + message)
    .digest();

  const hmac = crypto
    .createHmac("sha512", secret_buffer)
    .update(path + hash)
    .digest("base64");

  return hmac;
}

// ---------- Fetch Portfolio ----------
async function getBalances() {
  const path = "/0/private/Balance";
  const nonce = Date.now().toString();

  const request = { nonce };

  const signature = getKrakenSignature(
    path,
    request,
    API_SECRET,
    nonce
  );

  const response = await axios.post(
    BASE_URL + path,
    qs.stringify(request),
    {
      headers: {
        "API-Key": API_KEY,
        "API-Sign": signature,
        "Content-Type": "application/x-www-form-urlencoded",
      },
    }
  );

  return response.data.result;
}

// ---------- Fetch Market Data ----------
async function getTicker(pair) {
  const response = await axios.get(
    `${BASE_URL}/0/public/Ticker?pair=${pair}`
  );

  const key = Object.keys(response.data.result)[0];
  return response.data.result[key];
}

// ---------- Scoring Logic ----------
function scoreAsset(price, volume) {
  let score = 0;

  if (volume > 1000000) score += 3;
  if (price > 1) score += 1;
  if (price > 10) score += 1;
  if (price > 100) score += 1;

  return score;
}

// ---------- Routes ----------
app.get("/", (req, res) => {
  res.send("Structured Alpha Portfolio Engine Running");
});

app.get("/portfolio", async (req, res) => {
  try {
    const balances = await getBalances();

    const ownedAssets = Object.keys(balances)
      .filter(asset => parseFloat(balances[asset]) > 0)
      .filter(asset => asset !== "ZUSD");

    const portfolioResults = [];

    for (let asset of ownedAssets) {
      const pair = asset + "USD";

      try {
        const ticker = await getTicker(pair);

        const price = parseFloat(ticker.c[0]);
        const volume = parseFloat(ticker.v[1]);
        const score = scoreAsset(price, volume);

        let action = "HOLD";
        if (score >= 5) action = "ADD";
        if (score <= 2) action = "SELL";

        portfolioResults.push({
          asset,
          balance: balances[asset],
          price,
          volume,
          score,
          recommendation: action
        });

      } catch (e) {
        // skip invalid pairs
      }
    }

    // ---------- Scan Market For Buys ----------
    const scanPairs = [
      "XRPUSD",
      "SOLUSD",
      "SHIBUSD",
      "PEPEUSD"
    ];

    const buyOpportunities = [];

    for (let pair of scanPairs) {
      const ticker = await getTicker(pair);

      const price = parseFloat(ticker.c[0]);
      const volume = parseFloat(ticker.v[1]);
      const score = scoreAsset(price, volume);

      if (score >= 5) {
        buyOpportunities.push({
          pair,
          price,
          volume,
          score,
          action: "BUY"
        });
      }
    }

    res.json({
      portfolio_analysis: portfolioResults,
      buy_opportunities: buyOpportunities
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
})