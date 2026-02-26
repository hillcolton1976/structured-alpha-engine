const axios = require("axios");
const cron = require("node-cron");
const express = require("express");
const { RSI, EMA, MACD } = require("technicalindicators");

const app = express();
const PORT = process.env.PORT || 3000;

app.get("/", (req, res) => {
  res.send("Structured Alpha Engine Running");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

const KRAKEN_API = "https://api.kraken.com/0/public/OHLC";

async function fetchOHLC(pair) {
  const response = await axios.get(KRAKEN_API, {
    params: { pair: pair, interval: 60 }
  });
  const dataKey = Object.keys(response.data.result)[0];
  return response.data.result[dataKey].map(candle => ({
    close: parseFloat(candle[4]),
    high: parseFloat(candle[2]),
    low: parseFloat(candle[3]),
    volume: parseFloat(candle[6])
  }));
}

function calculateSignal(data) {
  const closes = data.map(d => d.close);
  const volumes = data.map(d => d.volume);

  const ema20 = EMA.calculate({ period: 20, values: closes });
  const ema50 = EMA.calculate({ period: 50, values: closes });
  const rsi = RSI.calculate({ period: 14, values: closes });
  const macd = MACD.calculate({
    values: closes,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9
  });

  const latestVolume = volumes[volumes.length - 1];
  const avgVolume =
    volumes.slice(-20).reduce((a, b) => a + b, 0) / 20;

  let score = 0;

  if (ema20[ema20.length - 1] > ema50[ema50.length - 1]) score += 20;
  if (rsi[rsi.length - 1] > 30) score += 20;
  if (macd[macd.length - 1].MACD > macd[macd.length - 1].signal) score += 20;
  if (latestVolume > avgVolume * 1.8) score += 20;

  const lastHigh = Math.max(...data.slice(-24).map(d => d.high));
  if (closes[closes.length - 1] > lastHigh) score += 20;

  return score;
}

async function scanMarket() {
  try {
    const pairs = ["XBTUSD", "ETHUSD", "SOLUSD"];
    for (let pair of pairs) {
      const data = await fetchOHLC(pair);
      const score = calculateSignal(data);

      if (score >= 75) {
        console.log(`🔥 Signal detected for ${pair} | Score: ${score}`);
      }
    }
  } catch (err) {
    console.error("Error scanning market:", err.message);
  }
}

cron.schedule("*/5 * * * *", () => {
  console.log("Running market scan...");
  scanMarket();
});
