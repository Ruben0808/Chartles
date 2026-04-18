import fs from "node:fs";
import path from "node:path";

export type Tier = "Stable" | "Moderate" | "Cautious" | "Risky" | "Speculative";

export interface Stock {
  symbol: string;
  name: string;
  price: number;
  change_1d_pct: number;
  change_1y_pct: number;
  rsi_14: number;
  sma_50: number;
  sma_200: number;
  above_200dma: boolean;
  dist_from_52w_high_pct: number;
  max_drawdown_1y_pct: number;
  volatility_1y_pct: number;
  avg_daily_value_cr: number;
  score: number;
  tier: Tier;
  reasons: string[];
}

export interface ScanPayload {
  generated_at: string;
  universe: string;
  count: number;
  failed: string[];
  stocks: Stock[];
}

export function loadStocks(): ScanPayload {
  const dataPath = path.join(process.cwd(), "..", "data", "stocks.json");
  const raw = fs.readFileSync(dataPath, "utf8");
  return JSON.parse(raw) as ScanPayload;
}
