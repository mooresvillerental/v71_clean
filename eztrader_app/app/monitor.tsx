import { View, Text, ScrollView } from "react-native";
import { useEffect, useState } from "react";

export default function Monitor() {
  const [data, setData] = useState<any>(null);

  async function load() {
    try {
      const r = await fetch("http://127.0.0.1:8000/latest-signal");
      const j = await r.json();
      setData(j);
    } catch (e) {
      console.log(e);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  if (!data) {
    return (
      <View style={{flex:1,justifyContent:"center",alignItems:"center"}}>
        <Text>Loading monitor...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={{padding:20}}>
      <Text style={{fontSize:22,fontWeight:"bold"}}>EZTrader Monitor</Text>

      <Text>Symbol: {data.symbol}</Text>
      <Text>Live Price: {data.live_price}</Text>
      <Text>Signal Price: {data.price}</Text>
      <Text>Action: {data.action}</Text>
      <Text>Final Action: {data.final_action}</Text>

      <Text>Confidence: {data.confidence}</Text>
      <Text>RSI: {data.rsi}</Text>

      <Text>Regime: {data.regime}</Text>
      <Text>Preferred Strategy: {data.preferred_strategy}</Text>

      <Text>Trade Eligible: {String(data.trade_eligible)}</Text>
      <Text>Quality Blocked: {String(data.quality_blocked)}</Text>

      <Text>Suggested Trade USD: {data.suggested_trade_usd}</Text>

      <Text>Timestamp: {data.timestamp}</Text>
    </ScrollView>
  );
}
