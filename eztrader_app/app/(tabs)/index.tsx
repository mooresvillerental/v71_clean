import { useEffect, useState } from "react";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from "react-native";

type Signal = {
  symbol: string;
  action: string;
  price: number;
  rsi?: number;
  confidence?: number;
  risk_level?: string;
  trend?: string;
  suggested_trade_usd?: number;
  timestamp?: number;
  strategy?: string;
};

type Portfolio = {
  cash_usd: number;
  holdings: Record<string, { qty: number; avg_price: number }>;
};

type Performance = {
  accepted_trades?: number;
  completed_sells?: number;
  wins?: number;
  losses?: number;
  win_rate?: number;
  realized_pnl_usd?: number;
  starting_portfolio_value?: number;
  current_portfolio_value?: number;
  return_pct?: number;
};

type TradeHistoryItem = {
  symbol: string;
  action: string;
  price: number;
  timestamp?: number;
  before_cash_usd?: number;
  before_qty?: number;
  before_avg_price?: number;
  filled_qty?: number;
  proceeds_usd?: number;
  realized_pnl_usd?: number;
  after_cash_usd?: number;
  after_qty?: number;
  after_avg_price?: number;
  size_usd?: number;
};

type Dashboard = {
  latest_signal: Signal | null;
  assistant_portfolio: Portfolio;
  assistant_performance?: Performance;
};

const API = "http://127.0.0.1:18093";

let lastAlert = "NONE";


async function registerForPushNotificationsAsync() {
  try {
    if (!Device.isDevice) {
      console.log("Push notifications require a physical device");
      return null;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      console.log("Push notification permission not granted");
      return null;
    }

    const tokenData = await Notifications.getExpoPushTokenAsync();
    const token = tokenData?.data || null;
    console.log("EXPO_PUSH_TOKEN:", token);
    return token;
  } catch (e) {
    console.log("Push registration error:", e);
    return null;
  }
}


let lastInAppSignal = "NONE";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState("");
  const [tradeHistory, setTradeHistory] = useState<TradeHistoryItem[]>([]);

  async function load() {
    try {
      const [dashRes, histRes, tradeRes] = await Promise.all([
        fetch(API + "/portfolio"),
        fetch(API + "/signal"),
        fetch(API + "/trade-history"),
      ]);

      const portfolioJson = await dashRes.json();
      const signalJson = await histRes.json();
      const tradeHistoryJson = await tradeRes.json();
      const liveSignal = signalJson?.signal || null;
      const liveAction = String(liveSignal?.action || "HOLD");
      const signalKey = liveSignal
        ? `${liveAction}|${liveSignal?.symbol || "?"}|${Number(liveSignal?.price || 0)}`
        : "NONE";

      const liveSuggestedTradeUsd =
        liveAction === "BUY"
          ? Number(liveSignal?.suggested_trade_usd ?? Math.max(0, Number(portfolioJson?.cash_usd ?? 0) * 0.2))
          : liveAction === "SELL"
          ? Number(
              liveSignal?.suggested_trade_usd ??
              Number(portfolioJson?.btc_qty ?? portfolioJson?.holdings_qty?.["BTC-USD"] ?? 0) *
                Number(liveSignal?.price ?? 0)
            )
          : 0;

      if ((liveAction === "BUY" || liveAction === "SELL") && signalKey !== lastInAppSignal) {
        lastInAppSignal = signalKey;
        Alert.alert(
          `${liveAction} SIGNAL`,
          `${liveSignal?.symbol || "BTC-USD"} @ $${Number(liveSignal?.price || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}\nSuggested: $${Number(liveSuggestedTradeUsd).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
        );
      } else if (liveAction !== "BUY" && liveAction !== "SELL") {
        lastInAppSignal = "NONE";
      }

      setData({
        cash_usd: Number(portfolioJson?.cash_usd ?? 0),
        portfolio_value: Number(portfolioJson?.portfolio_value ?? 0),
        unrealized_pl: Number(portfolioJson?.unrealized_pl ?? 0),
        btc_qty: Number(portfolioJson?.btc_qty ?? portfolioJson?.holdings_qty?.["BTC-USD"] ?? 0),
        avg_price: Number(portfolioJson?.avg_price ?? 0),
        current_price: Number(portfolioJson?.current_price ?? 0),
        latest_signal: liveSignal,
        assistant_portfolio: {
          cash_usd: Number(portfolioJson?.cash_usd ?? 0),
          holdings: {
            "BTC-USD": {
              qty: Number(portfolioJson?.btc_qty ?? portfolioJson?.holdings_qty?.["BTC-USD"] ?? 0),
              avg_price: Number(portfolioJson?.avg_price ?? 0),
            },
          },
        },
        assistant_performance: {
          starting_portfolio_value: Number(portfolioJson?.portfolio_value ?? 0),
          current_portfolio_value: Number(portfolioJson?.portfolio_value ?? 0),
          realized_pl: 0,
        },
      });
      setTradeHistory(Array.isArray(tradeHistoryJson?.trades) ? tradeHistoryJson.trades : []);
    } catch (e) {
      console.log(e);
    }
  }

  async function acceptTrade() {
    setLoading(true);

    try {
      const r = await fetch(API + "/confirm", { method: "POST" });
      const j = await r.json();

      if (j.status === "trade_applied") {
        const p = j.portfolio;
        const h = p.holdings["BTC-USD"] || { qty: 0, avg_price: 0 };

        const msg =
          `Cash: ${Number(data?.cash_usd ?? 0).toFixed(2)}\n` +
          `BTC: ${Number(h.qty || 0).toFixed(8)}\n` +
          `Avg Entry Price: $${Number(h.avg_price || 0).toFixed(2)}`;

        setLastResult(msg);
        Alert.alert("Trade Executed", msg);
      } else {
        setLastResult(`Blocked: ${j.reason}`);
        Alert.alert("Blocked", j.reason);
      }

      load();
    } catch (e) {
      Alert.alert("Error", "Could not execute trade");
    }

    setLoading(false);
  }

  function denyTrade() {
    setLastResult("Trade denied");
    Alert.alert("Trade Denied", "Signal ignored");
  }

  useEffect(() => {
    registerForPushNotificationsAsync();
    load();
    const id = setInterval(load, 5000);
    
      return () => clearInterval(id);
  }, []);

  if (!data) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  const signal = data.latest_signal;
  const portfolio = {
    cash_usd: Number((data as any)?.cash_usd ?? 0),
    total_value: Number((data as any)?.portfolio_value ?? 0),
    unrealized_pl: Number((data as any)?.unrealized_pl ?? 0),
    high_water_price: Number((data as any)?.high_water_price ?? 0),
    trailing_stop_price: Number((data as any)?.trailing_stop_price ?? 0),
    holdings: {
      "BTC-USD": {
        qty: Number((data as any)?.btc_qty ?? (data as any)?.holdings_qty?.["BTC-USD"] ?? 0),
        avg_price: Number((data as any)?.avg_price ?? 0),
        current_price: Number((data as any)?.current_price ?? 0),
      },
    },
  };
  const perf = data?.assistant_performance || {};
  const holding = portfolio?.holdings?.["BTC-USD"] || { qty: 0, avg_price: 0 };

  const signalStrength = Math.max(0, Math.min(100, Number(signal?.confidence || 0)));
  const strengthBars = Math.max(1, Math.min(10, Math.round(signalStrength / 10)));
  const strengthLabel =
    signalStrength >= 80 ? "Very Strong" :
    signalStrength >= 65 ? "Strong" :
    signalStrength >= 50 ? "Moderate" :
    signalStrength > 0 ? "Weak" : "None";

    let disabledReason = "";
    let acceptDisabled = false;

    const rawAction = signal?.action || "NONE";
    const tradeApproved =
      !!signal &&
      (rawAction === "BUY" || rawAction === "SELL") &&
      signal.quality_blocked !== true &&
      signal.trade_eligible === true;

    const displayAction = tradeApproved ? rawAction : "HOLD";

    if (signal) {
      if (!tradeApproved) {
        acceptDisabled = true;
        disabledReason =
          signal.quality_reason ||
          signal.eligibility_reason ||
          "Trade not approved";
      }

      if (tradeApproved && rawAction === "SELL" && holding.qty <= 0) {
        acceptDisabled = true;
        disabledReason = "No BTC available to sell";
      }

      if (
        tradeApproved &&
        rawAction === "BUY" &&
        portfolio.cash_usd < (signal.suggested_trade_usd || 0)
      ) {
        acceptDisabled = true;
        disabledReason = "Not enough cash to execute trade";
      }
    }

  const portfolioValue = portfolio.cash_usd + holding.qty * (signal?.price || 0);
  const costBasis = holding.qty * holding.avg_price;
  const unrealizedPnL =
    holding.qty > 0 ? holding.qty * (signal?.price || 0) - costBasis : 0;
  const trailingStopPrice = Number((portfolio as any)?.trailing_stop_price ?? 0);
  const stopTriggered =
    holding.qty > 0 &&
    trailingStopPrice > 0 &&
    Number(signal?.price || holding.current_price || 0) <= trailingStopPrice;

  const suggestedTradeUsd =
    rawAction === "BUY"
      ? Number(signal?.suggested_trade_usd ?? Math.max(0, portfolio.cash_usd * 0.2))
      : rawAction === "SELL"
      ? Number(signal?.suggested_trade_usd ?? holding.qty * Number(signal?.price || 0))
      : 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>EZTRADER</Text>
      <Text style={styles.subtitle}>Assistant Mode</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Latest Signal</Text>

        {signal ? (
          <>
            <View style={styles.topRow}>
              <Text style={styles.symbol}>{signal.symbol}</Text>

              <View
                style={[
                  styles.badge,
                  displayAction === "BUY" ? styles.buy : displayAction === "SELL" ? styles.sell : styles.hold,
                ]}
              >
                <Text style={styles.badgeText}>{displayAction}</Text>
              </View>
            </View>

              <Text style={styles.price}>
                ${Number(signal.live_price ?? signal.price ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Text>
              <Text style={styles.meta}>
                Signal Price: ${Number(signal.price ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Text>
              <Text style={styles.meta}>
                RSI: {signal.rsi != null ? Number(signal.rsi).toFixed(1) : "-"}
              </Text>
              <Text style={styles.meta}>
                Confidence: {signal.confidence != null ? `${signal.confidence}%` : "-"}
              </Text>
              <Text style={styles.meta}>
                Strategy: {signal.winning_strategy ?? signal.strategy ?? "-"}
              </Text>
              <Text style={styles.meta}>Risk: {signal.risk_level ?? "-"}</Text>
              <Text style={styles.meta}>Trend: {signal.trend ?? "-"}</Text>
              <Text style={styles.meta}>Regime: {signal.regime ?? "-"}</Text>
              <Text style={styles.meta}>
                Signal Age: {signal.timestamp ? `${Math.max(0, Math.floor(Date.now() / 1000 - Number(signal.timestamp)))}s ago` : "-"}
              </Text>

              {rawAction !== "HOLD" && (
                <>
                  <Text style={styles.tradeBox}>
                    Suggested Trade: ${Number(suggestedTradeUsd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </Text>

                  <Text style={styles.meta}>
                    Stop Loss: {signal?.stop_loss_price ? `$${Number(signal.stop_loss_price).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "-"}
                  </Text>
                </>
              )}

            <View style={styles.strengthBox}>
              <View style={styles.topRow}>
                <Text style={styles.resultTitle}>Signal Strength</Text>
                <Text style={styles.resultText}>{signalStrength}%</Text>
              </View>
              <View style={styles.strengthTrack}>
                <View style={[styles.strengthFill, { width: `${strengthBars * 10}%` }]} />
              </View>
              <Text style={styles.meta}>Quality: {strengthLabel}</Text>
            </View>

            {disabledReason && (
              <Text style={styles.warning}>{disabledReason}</Text>
            )}

            <View style={styles.row}>
              <TouchableOpacity
                style={[
                  styles.accept,
                  acceptDisabled && styles.disabledButton,
                ]}
                disabled={acceptDisabled || loading || !tradeApproved}
                onPress={acceptTrade}
              >
                <Text style={styles.btnText}>ACCEPT TRADE</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.deny,
                  (acceptDisabled || loading || !tradeApproved) && styles.disabledButton,
                ]}
                disabled={acceptDisabled || loading || !tradeApproved}
                onPress={denyTrade}>
                <Text style={styles.btnText}>DENY</Text>
              </TouchableOpacity>
            </View>

            {lastResult ? (
              <View style={styles.resultBox}>
                <Text style={styles.resultTitle}>Last Trade Result</Text>
                <Text style={styles.resultText}>{lastResult}</Text>
              </View>
            ) : null}
          </>
        ) : (
          <Text style={styles.meta}>No signal</Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Portfolio</Text>

        <Text style={styles.cash}>
          Cash: ${Number(data?.cash_usd ?? 0).toFixed(2)}
        </Text>

        <View style={styles.holdingBox}>
          <Text style={styles.meta}>BTC-USD</Text>
          <Text style={styles.meta}>Qty: {holding.qty}</Text>
          <Text style={styles.meta}>Avg Entry Price: ${holding.avg_price}</Text>
        </View>

        <View style={styles.resultBox}>
          <Text style={styles.resultTitle}>Portfolio Value</Text>
          <Text style={styles.resultText}>${portfolioValue.toFixed(2)}</Text>
          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Unrealized P/L</Text>
          <Text style={styles.resultText}>${unrealizedPnL.toFixed(2)}</Text>
          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Trailing Stop</Text>
          <Text style={styles.resultText}>
            {trailingStopPrice > 0 ? `$${trailingStopPrice.toFixed(2)}` : "-"}
          </Text>
          {stopTriggered ? (
            <Text style={styles.warning}>STOP TRIGGERED — position is below protective stop</Text>
          ) : null}
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Assistant Performance</Text>

        <View style={styles.perfGrid}>
          <View style={styles.perfBox}>
            <Text style={styles.perfLabel}>Accepted Trades</Text>
            <Text style={styles.perfValue}>{perf.accepted_trades ?? 0}</Text>
          </View>

          <View style={styles.perfBox}>
            <Text style={styles.perfLabel}>Win Rate</Text>
            <Text style={styles.perfValue}>{perf.win_rate ?? 0}%</Text>
          </View>

          <View style={styles.perfBox}>
            <Text style={styles.perfLabel}>Wins</Text>
            <Text style={styles.perfValue}>{perf.wins ?? 0}</Text>
          </View>

          <View style={styles.perfBox}>
            <Text style={styles.perfLabel}>Losses</Text>
            <Text style={styles.perfValue}>{perf.losses ?? 0}</Text>
          </View>
        </View>

        <View style={styles.resultBox}>
          <Text style={styles.resultTitle}>Starting Portfolio Value</Text>
          <Text style={styles.resultText}>${Number(perf.starting_portfolio_value || 0).toFixed(2)}</Text>

          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Current Portfolio Value</Text>
          <Text style={styles.resultText}>${Number(perf.current_portfolio_value || 0).toFixed(2)}</Text>

          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Realized P/L</Text>
          <Text style={styles.resultText}>${Number(perf.realized_pnl_usd || 0).toFixed(2)}</Text>

          <Text style={[styles.resultTitle, { marginTop: 10 }]}>Return %</Text>
          <Text style={styles.resultText}>{Number(perf.return_pct || 0).toFixed(2)}%</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Trade History</Text>

        {tradeHistory.length === 0 ? (
          <Text style={styles.meta}>No accepted trades yet.</Text>
        ) : (
          tradeHistory
            .slice()
            .reverse()
            .map((item, i) => (
              <View key={i} style={styles.historyBox}>
                <View style={styles.topRow}>
                  <Text style={styles.historyTitle}>
                    {item.action} {item.symbol}
                  </Text>
                  <View
                    style={[
                      styles.badge,
                      item.action === "BUY" ? styles.buy : styles.sell,
                    ]}
                  >
                    <Text style={styles.badgeText}>{item.action}</Text>
                  </View>
                </View>

                <Text style={styles.meta}>Price: ${Number(item.price || 0).toFixed(2)}</Text>

                {item.action === "BUY" ? (
                  <>
                    <Text style={styles.meta}>Size USD: ${Number(item.size_usd || 0).toFixed(2)}</Text>
                    <Text style={styles.meta}>Filled Qty: {Number(item.filled_qty || 0).toFixed(8)}</Text>
                  </>
                ) : (
                  <>
                    <Text style={styles.meta}>Filled Qty: {Number(item.filled_qty || 0).toFixed(8)}</Text>
                    <Text style={styles.meta}>Proceeds: ${Number(item.proceeds_usd || 0).toFixed(2)}</Text>
                    <Text style={styles.meta}>Realized P/L: ${Number(item.realized_pnl_usd || 0).toFixed(2)}</Text>
                  </>
                )}
              </View>
            ))
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{flex:1,backgroundColor:"#0f172a"},
  content:{padding:20},

  center:{flex:1,justifyContent:"center",alignItems:"center",backgroundColor:"#0f172a"},

  title:{color:"white",fontSize:30,fontWeight:"bold"},
  subtitle:{color:"#94a3b8",marginBottom:20},

  card:{backgroundColor:"#1e293b",padding:16,borderRadius:14,marginBottom:14},

  cardTitle:{color:"white",fontSize:18,fontWeight:"bold",marginBottom:10},

  topRow:{flexDirection:"row",justifyContent:"space-between",alignItems:"center"},

  symbol:{color:"white",fontSize:22,fontWeight:"bold"},

  badge:{paddingHorizontal:14,paddingVertical:8,borderRadius:999},
  buy:{backgroundColor:"#22c55e"},
  sell:{backgroundColor:"#ef4444"},

  badgeText:{color:"white",fontWeight:"bold"},

  price:{color:"white",fontSize:26,fontWeight:"bold",marginTop:10},

  meta:{color:"#cbd5e1"},

  tradeBox:{backgroundColor:"#334155",padding:10,borderRadius:10,marginTop:10,color:"#7dd3fc"},

  warning:{color:"#facc15",marginTop:8},

  row:{flexDirection:"row",marginTop:14},

  accept:{flex:1,backgroundColor:"#22c55e",padding:12,borderRadius:10,marginRight:8},
  deny:{flex:1,backgroundColor:"#475569",padding:12,borderRadius:10},

  disabledButton:{backgroundColor:"#1f2937"},

  btnText:{textAlign:"center",color:"white",fontWeight:"bold"},

  resultBox:{backgroundColor:"#020617",padding:12,borderRadius:10,marginTop:14},
  resultTitle:{color:"#7dd3fc",marginBottom:6,fontWeight:"bold"},
  resultText:{color:"#e2e8f0"},

  cash:{color:"#7dd3fc",fontSize:22,fontWeight:"bold",marginBottom:10},

  holdingBox:{backgroundColor:"#334155",padding:12,borderRadius:10},

  perfGrid:{
    flexDirection:"row",
    flexWrap:"wrap",
    justifyContent:"space-between"
  },

  perfBox:{
    width:"48%",
    backgroundColor:"#334155",
    padding:12,
    borderRadius:10,
    marginBottom:10
  },

  perfLabel:{
    color:"#94a3b8",
    fontSize:13,
    marginBottom:4
  },

  perfValue:{
    color:"white",
    fontSize:20,
    fontWeight:"bold"
  },

  historyBox:{
    backgroundColor:"#334155",
    padding:12,
    borderRadius:10,
    marginTop:10
  },

  historyTitle:{
    color:"white",
    fontSize:16,
    fontWeight:"bold"
  },

  strengthBox:{
    backgroundColor:"#020617",
    padding:12,
    borderRadius:10,
    marginTop:14
  },

  strengthTrack:{
    height:10,
    backgroundColor:"#334155",
    borderRadius:999,
    overflow:"hidden",
    marginTop:8,
    marginBottom:8
  },

  strengthFill:{
    height:"100%",
    backgroundColor:"#38bdf8"
  }
});
