import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chartles",
  description: "Personal BSE/NSE research dashboard. Research tool, not a predictor.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="container">
            <h1 className="logo">
              Chartles<span className="logo-dot">.</span>
            </h1>
            <p className="tagline">Research over prediction — BSE/NSE scanner</p>
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="site-footer">
          <div className="container">
            <p>
              Chartles is a research tool, not investment advice. Health scores combine
              technical posture, volatility, liquidity, and momentum — they do not predict
              future returns.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
