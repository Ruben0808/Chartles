import { loadStocks, type Stock } from "@/lib/data";

export const dynamic = "force-static";

export default function HomePage() {
  const data = loadStocks();
  const tierCounts = countByTier(data.stocks);

  return (
    <>
      <h2 className="page-title">Nifty 50 — ranked by health score</h2>
      <p className="page-meta">
        {data.count} symbols · last scan {formatDate(data.generated_at)}
        {data.failed.length > 0 && ` · ${data.failed.length} failed`}
      </p>

      <div className="summary-grid">
        {(["Stable", "Moderate", "Cautious", "Risky", "Speculative"] as const).map((t) => (
          <div key={t} className="summary-card">
            <div className="label">{t}</div>
            <div className="value">{tierCounts[t] ?? 0}</div>
          </div>
        ))}
      </div>

      {data.stocks.length === 0 ? (
        <div className="empty-state">
          No scan data yet. Run <code>python scanner/run.py</code> to populate{" "}
          <code>data/stocks.json</code>.
        </div>
      ) : (
        <table className="stock-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Tier</th>
              <th className="num">Score</th>
              <th className="num">Price</th>
              <th className="num">1d</th>
              <th className="num">1y</th>
              <th className="num">RSI</th>
              <th className="num">From 52wH</th>
              <th className="num">Vol 1y</th>
              <th>Signals</th>
            </tr>
          </thead>
          <tbody>
            {data.stocks.map((s) => (
              <tr key={s.symbol}>
                <td>
                  <strong>{s.symbol}</strong>
                </td>
                <td>
                  <span className={`tier-badge tier-${s.tier}`}>{s.tier}</span>
                </td>
                <td className="num">{s.score}</td>
                <td className="num">₹{s.price.toLocaleString("en-IN")}</td>
                <td className={`num ${s.change_1d_pct >= 0 ? "pos" : "neg"}`}>
                  {fmtPct(s.change_1d_pct)}
                </td>
                <td className={`num ${s.change_1y_pct >= 0 ? "pos" : "neg"}`}>
                  {fmtPct(s.change_1y_pct)}
                </td>
                <td className="num">{s.rsi_14.toFixed(0)}</td>
                <td className="num">{fmtPct(s.dist_from_52w_high_pct)}</td>
                <td className="num">{s.volatility_1y_pct.toFixed(0)}%</td>
                <td className="reasons">{s.reasons.join(" · ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function countByTier(stocks: Stock[]): Record<string, number> {
  return stocks.reduce<Record<string, number>>((acc, s) => {
    acc[s.tier] = (acc[s.tier] ?? 0) + 1;
    return acc;
  }, {});
}

function fmtPct(n: number): string {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
