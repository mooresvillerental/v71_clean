import { useEffect, useState } from "react";
import { Text, View, StyleSheet, ScrollView } from "react-native";

export default function App() {

  const [data,setData] = useState(null)

  async function load(){
    const r = await fetch("http://127.0.0.1:8000/dashboard")
    const j = await r.json()
    setData(j)
  }

  useEffect(()=>{
    load()
    const i = setInterval(load,5000)
    return ()=>clearInterval(i)
  },[])

  if(!data) return <Text>Loading...</Text>

  return (

    <ScrollView style={styles.container}>

      <Text style={styles.title}>EZTRADER</Text>

      <View style={styles.card}>
        <Text style={styles.heading}>Latest Signal</Text>
        <Text>
          {data.latest_signal.action} {data.latest_signal.symbol}
        </Text>
        <Text>${data.latest_signal.price}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.heading}>Stats</Text>
        <Text>Win Rate: {data.stats.win_rate}%</Text>
        <Text>Trades: {data.stats.total_trades}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.heading}>Recent Signals</Text>
        {data.recent_signals.map((s,i)=>(
          <Text key={i}>
            {s.action} {s.symbol} ${s.price}
          </Text>
        ))}
      </View>

    </ScrollView>

  )
}

const styles = StyleSheet.create({

container:{
  backgroundColor:"#0f172a",
  padding:30
},

title:{
  color:"white",
  fontSize:28,
  marginBottom:20
},

card:{
  backgroundColor:"#1e293b",
  padding:20,
  borderRadius:10,
  marginBottom:15
},

heading:{
  color:"white",
  fontSize:18,
  marginBottom:10
}

})

