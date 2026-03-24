import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from "react-native";

const API = "http://127.0.0.1:8000";

export default function Settings() {

  const [cash,setCash] = useState("1500");
  const [btcQty,setBtcQty] = useState("0.01");
  const [avgPrice,setAvgPrice] = useState("45000");

  async function savePortfolio(){

    const payload = {
      cash_usd: parseFloat(cash),
      holdings:{
        "BTC-USD":{
          qty: parseFloat(btcQty),
          avg_price: parseFloat(avgPrice)
        }
      }
    };

    try{

      const r = await fetch(API + "/assistant-set-portfolio",{
        method:"POST",
        headers:{
          "Content-Type":"application/json"
        },
        body:JSON.stringify(payload)
      });

      const j = await r.json();

      if(j.status==="portfolio_updated"){
        Alert.alert("Saved","Portfolio updated");
      }

    }catch(e){
      Alert.alert("Error","Connection failed");
    }

  }

  async function resetSession(){

    try{

      const r = await fetch(API + "/assistant-reset-session",{method:"POST"});
      const j = await r.json();

      if(j.status==="session_reset"){
        Alert.alert("Reset Complete","New testing session started");
      }

    }catch(e){
      Alert.alert("Error","Could not reset session");
    }

  }

  return(

    <View style={styles.container}>

      <Text style={styles.title}>Portfolio Settings</Text>

      <Text style={styles.label}>Cash USD</Text>
      <TextInput style={styles.input} value={cash} onChangeText={setCash} keyboardType="numeric"/>

      <Text style={styles.label}>BTC Quantity</Text>
      <TextInput style={styles.input} value={btcQty} onChangeText={setBtcQty} keyboardType="numeric"/>

      <Text style={styles.label}>BTC Average Price</Text>
      <TextInput style={styles.input} value={avgPrice} onChangeText={setAvgPrice} keyboardType="numeric"/>

      <TouchableOpacity style={styles.saveBtn} onPress={savePortfolio}>
        <Text style={styles.saveText}>SAVE PORTFOLIO</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.resetBtn} onPress={resetSession}>
        <Text style={styles.saveText}>START NEW TEST SESSION</Text>
      </TouchableOpacity>

    </View>

  );

}

const styles = StyleSheet.create({

container:{
flex:1,
backgroundColor:"#0f172a",
padding:20
},

title:{
color:"white",
fontSize:24,
fontWeight:"bold",
marginBottom:20
},

label:{
color:"#94a3b8",
marginTop:12
},

input:{
backgroundColor:"#1e293b",
color:"white",
padding:12,
borderRadius:10,
marginTop:6
},

saveBtn:{
backgroundColor:"#22c55e",
padding:14,
borderRadius:10,
marginTop:30
},

resetBtn:{
backgroundColor:"#ef4444",
padding:14,
borderRadius:10,
marginTop:12
},

saveText:{
color:"white",
textAlign:"center",
fontWeight:"bold"
}

});
