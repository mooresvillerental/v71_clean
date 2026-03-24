import { ScrollView, Text, View } from "react-native";
import { useEffect, useState } from "react";

const API = "http://127.0.0.1:18093";

type SignalData = {
  symbol?: string;
  action?: string;
  final_action?: string;
  price?: number;
  live_price?: number;
  rsi?: number;
  confidence?: number;
  strategy?: string;
  winning_strategy?: string;
  preferred_strategy?: string;
  regime?: string;
  trend?: string;
  trade_eligible?: boolean;
  eligibility_reason?: string;
  quality_blocked?: boolean;
  quality_reason?: string;
  suggested_trade_usd?: number;
  timestamp?: number;
};

type ShadowRow = {
  opened_timestamp?: number;
  exit_timestamp?: number;
  symbol?: string;
  action?: string;
  strategy?: string;
  winning_strategy?: string;
  regime?: string;
  confidence?: number;
  entry_price?: number;
  exit_price?: number;
  pnl_pct?: number;
  outcome?: string;
};

type ShadowStats = {
  open_count: number;
  closed_count: number;
  blocked_count: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  avg_pnl_pct: number;
  last_closed?: ShadowRow | null;
};

type StrategyStat = {
  strategy: string;
  trades: number;
  wins: number;
  win_rate: number;
  avg_pnl: number;
};

type MonitorData = {
  latest_signal?: SignalData;
  shadow?: ShadowStats;
  strategies?: StrategyStat[];
};

export default function MonitorTab() {
  const [data, setData] = useState<MonitorData | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setError("");

      const [signalRes, shadowRes, strategyRes] = await Promise.all([
        fetch(API + "/signal", { cache: "no-store" }),
        fetch(API + "/shadow-stats", { cache: "no-store" }),
        fetch(API + "/shadow-last-closed", { cache: "no-store" }),
      ]);

      const signalWrap = await signalRes.json();
      const signal = signalWrap?.signal || null;
      const shadow = await shadowRes.json();
      const lastClosedWrap = await strategyRes.json();
      const strategies = [];

      setData({
        latest_signal: signal,
        shadow: {
          ...(shadow || {}),
          last_closed: lastClosedWrap?.trade || lastClosedWrap?.last_closed || shadow?.last_closed || null,
        },
        strategies,
      });
    } catch {
      setError("Could not load monitor data");
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const row = (label: string, value: string | number | boolean | null | undefined) => (
    <View
      key={label}
      style={{
        flexDirection: "row",
        justifyContent: "space-between",
        paddingVertical: 8,
        borderBottomWidth: 1,
        borderBottomColor: "#334155",
      }}
    >
      <Text style={{ color: "#94a3b8", flex: 1 }}>{label}</Text>
      <Text style={{ color: "#e2e8f0", flex: 1, textAlign: "right" }}>
        {value == null || value === "" ? "-" : String(value)}
      </Text>
    </View>
  );

  const cardStyle = {
    backgroundColor: "#1e293b",
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  } as const;

  const signal = data?.latest_signal;
  const shadow = data?.shadow;
  const lastClosed = shadow?.last_closed;
  const strategies = data?.strategies ?? [];

  const probabilityBlock = () => {
    if (!signal) return null;

    let probability = Number(signal.confidence ?? 0);

    if (signal.action === "BUY" || signal.action === "SELL") probability += 15;
    else probability -= 10;

    if (signal.trade_eligible === true) probability += 10;
    if (signal.quality_blocked === true) probability -= 20;

    probability = Math.max(0, Math.min(100, probability));

    const label =
      probability >= 80 ? "High" :
      probability >= 60 ? "Strong" :
      probability >= 40 ? "Building" :
      "Weak";

    return (
      <>
        {row("Probability", `${probability}%`)}
        {row("State", label)}
      </>
    );
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: "#0f172a" }}
      contentContainerStyle={{ padding: 20 }}
    >
      <Text style={{ color: "#f8fafc", fontSize: 28, fontWeight: "700" }}>
        Monitor
      </Text>
      <Text style={{ color: "#94a3b8", marginTop: 4, marginBottom: 16 }}>
        EZTrader live diagnostics
      </Text>

      {error ? <Text style={{ color: "#f87171", marginBottom: 16 }}>{error}</Text> : null}

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Latest Signal
        </Text>
        {!signal ? (
          <Text style={{ color: "#cbd5e1" }}>Loading...</Text>
        ) : (
          <>
            {row("Symbol", signal.symbol)}
            {row("Action", signal.action)}
            {row("Final Action", signal.final_action)}
            {row("Live Price", signal.live_price)}
            {row("Signal Price", signal.price)}
            {row("RSI", signal.rsi != null ? Number(signal.rsi).toFixed(1) : "-")}
            {row("Confidence", signal.confidence != null ? `${signal.confidence}%` : "-")}
            {row("Strategy", signal.strategy)}
            {row("Winning Strategy", signal.winning_strategy)}
            {row("Preferred Strategy", signal.preferred_strategy)}
            {row("Regime", signal.regime)}
            {row("Trend", signal.trend)}
            {row("Trade Eligible", signal.trade_eligible)}
            {row("Eligibility Reason", signal.eligibility_reason)}
            {row("Quality Blocked", signal.quality_blocked)}
            {row("Quality Reason", signal.quality_reason)}
            {row("Suggested USD", signal.suggested_trade_usd)}
            {row("Timestamp", signal.timestamp)}
          </>
        )}
      </View>

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Feed Health
        </Text>
        {signal ? (
          <>
            {row("Signal Timestamp", signal.timestamp)}
            {row("Signal Age (seconds)", signal.timestamp ? Math.round(Date.now() / 1000 - signal.timestamp) : "-")}
            {row("Feed Status", signal.timestamp && Date.now() / 1000 - signal.timestamp < 15 ? "LIVE" : "STALE")}
          </>
        ) : (
          <Text style={{ color: "#cbd5e1" }}>Loading...</Text>
        )}
      </View>

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Shadow Performance
        </Text>
        {!shadow ? (
          <Text style={{ color: "#cbd5e1" }}>Loading...</Text>
        ) : (
          <>
            {row("Open Trades", shadow.open_count)}
            {row("Closed Trades", shadow.closed_count)}
            {row("Blocked Candidates", shadow.blocked_count)}
            {row("Wins", shadow.wins)}
            {row("Losses", shadow.losses)}
            {row("Win Rate", `${(Number(shadow?.win_rate_pct ?? 0)).toFixed(1)}%`)}
            {row("Avg P/L", `${(Number(shadow?.avg_pnl_pct ?? 0)).toFixed(2)}%`)}
          </>
        )}
      </View>

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Strategy Intelligence
        </Text>
        {strategies.length === 0 ? (
          <Text style={{ color: "#cbd5e1" }}>No strategy results yet.</Text>
        ) : (
          strategies.map((s, idx) => (
            <View key={`${s.strategy}-${idx}`} style={{ marginBottom: 14 }}>
              <Text style={{ color: "#f8fafc", fontWeight: "700", marginBottom: 6 }}>
                {s.strategy}
              </Text>
              {row("Trades", s.trades)}
              {row("Wins", s.wins)}
              {row("Win Rate", `${Number(s.win_rate).toFixed(1)}%`)}
              {row("Avg P/L", `${Number(s.avg_pnl).toFixed(2)}%`)}
            </View>
          ))
        )}
      </View>

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Trade Probability Meter
        </Text>
        {!signal ? (
          <Text style={{ color: "#cbd5e1" }}>Loading...</Text>
        ) : (
          probabilityBlock()
        )}
      </View>

      <View style={cardStyle}>
        <Text style={{ color: "#f8fafc", fontSize: 20, fontWeight: "700", marginBottom: 12 }}>
          Last Closed Shadow
        </Text>
        {!lastClosed ? (
          <Text style={{ color: "#cbd5e1" }}>No closed shadow trade available yet.</Text>
        ) : (
          <>
            {row("Symbol", lastClosed.symbol)}
            {row("Action", lastClosed.action)}
            {row("Strategy", lastClosed.winning_strategy || lastClosed.strategy)}
            {row("Regime", lastClosed.regime)}
            {row("Entry", lastClosed.entry_price)}
            {row("Exit", lastClosed.exit_price)}
            {row("P/L %", lastClosed.pnl_pct != null ? `${Number(lastClosed.pnl_pct).toFixed(2)}%` : "-")}
            {row("Outcome", lastClosed.outcome)}
          </>
        )}
      </View>
    </ScrollView>
  );
}
