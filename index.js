const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

/* ===============================
   SIMULATED PORTFOLIO
================================= */
const portfolio = {
  XRPUSD: 500,
  SOLUSD: 25,
  SHIBUSD: 1000000,
  PEPEUSD: 5000000,
  COQUSD: 100000
};

/* ===============================
   SCANNER ENGINE
================================= */
async function scanMarket() {
  const assetPairs = await axios.get(
    "https://api.kraken.com/0/public/AssetPairs"
  );

  const allPairs = Object.values(assetPairs.data.result);

  const usdPairs = allPairs
    .filter(p => p.wsname && p.wsname.endsWith("/USD"))
    .map(p => p.altname);

  const pairsToScan = usdPairs.slice(0, 30);

  const requests = pairsToScan.map(pair =>
    axios.get(`https://api.kraken.com/0/public/Ticker?pair=${pair}`)
  );

  const responses = await Promise.allSettled(requests);

  let results = [];

  responses.forEach((res, index) => {
    if (res.status !== "fulfilled") return;

    const pair = pairsToScan[index];
    const dataKey = Object.keys(res.value.data.result)[0];
    const ticker = res.value.data.result[dataKey];

    const price = parseFloat(ticker.c[0]);
    const volume = parseFloat(ticker.v[1]);
    const high = parseFloat(ticker.h[1]);
    const low = parseFloat(ticker.l[1]);
    const open = parseFloat(ticker.o);

    const changePercent = ((price - open) / open) * 100;
    const volatility = ((high - low) / low) * 100;

    let score = 0;

    if (volume > 5000000) score += 3;
    else if (volume > 1000000) score += 2;

    if (changePercent > 3) score += 3;
    else if (changePercent > 1) score += 2;

    if (volatility > 5) score += 2;

    if (price > 0.01) score += 1;

    results.push({
      pair,
      price,
      changePercent: changePercent.toFixed(2),
      volatility: volatility.toFixed(2),
      score
    });
  });

  results.sort((a, b) => b.score - a.score);

  return results;
}

/* ===============================
   DASHBOARD
================================= */
app.get("/", async (req, res) => {
  try {
    const market = await scanMarket();

    // Portfolio evaluation
    let portfolioRows = Object.keys(portfolio).map(pair => {
      const asset = market.find(m => m.pair === pair);

      if (!asset) {
        return `
          <tr>
            <td>${pair}</td>
            <td colspan="4">Not available on Kraken USD</td>
          </tr>
        `;
      }

      let action = "HOLD";
      let color = "#ffd700";

      if (asset.score >= 7) {
        action = "ADD";
        color = "#00ff88";
      } else if (asset.score <= 2) {
        action = "SELL";
        color = "#ff4d4d";
      }

      return `
        <tr>
          <td>${pair}</td>
          <td>$${asset.price.toFixed(4)}</td>
          <td>${asset.changePercent}%</td>
          <td>${asset.score}</td>
          <td style="color:${color}; font-weight:bold;">
            ${action}
          </td>
        </tr>
      `;
    }).join("");

    // New BUY opportunities (not in portfolio)
    const buys = market
      .filter(m => !portfolio[m.pair] && m.score >= 7)
      .slice(0, 5);

    let buyRows = buys.map(r => `
      <tr>
        <td>${r.pair}</td>
        <td>$${r.price.toFixed(4)}</td>
        <td>${r.changePercent}%</td>
        <td>${r.score}</td>
        <td style="color:#00ff88; font-weight:bold;">BUY</td>
        <td>
          <a href="https://trade.kraken.com/charts/KRAKEN:${r.pair}"
             target="_blank"
             style="
               background:#00ff88;
               color:black;
               padding:6px 12px;
               border-radius:8px;
               text-decoration:none;
               font-weight:bold;">
            TRADE
          </a>
        </td>
      </tr>
    `).join("");

    res.send(`
      <html>
      <head>
        <title>Structured Alpha Portfolio Assistant</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="20">
        <style>
          body { background:#0f172a; color:white; font-family:Arial; padding:20px; }
          h1 { text-align:center; }
          table { width:100%; border-collapse:collapse; margin-top:20px; }
          th, td { padding:10px; border-bottom:1px solid #334155; text-align:center; }
          th { background:#1e293b; }
          tr:hover { background:#1e293b; }
          h2 { margin-top:40px; }
        </style>
      </head>
      <body>
        <h1>📊 Structured Alpha Portfolio Assistant</h1>

        <h2>🧾 Your Portfolio</h2>
        <table>
          <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Score</th>
            <th>Recommendation</th>
          </tr>
          ${portfolioRows}
        </table>

        <h2>🚀 New Buy Opportunities</h2>
        <table>
          <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Score</th>
            <th>Signal</th>
            <th>Trade</th>
          </tr>
          ${buyRows || "<tr><td colspan='6'>No strong buys right now</td></tr>"}
        </table>

        <p style="text-align:center; margin-top:20px; opacity:0.6;">
          Simulated Mode – No API Keys Connected
        </p>
      </body>
      </html>
    `);

  } catch (error) {
    res.send("Engine error");
  }
});

app.listen(PORT, () => {
  console.log("Portfolio Assistant running on port " + PORT);
});