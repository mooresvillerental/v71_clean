import { Tabs } from "expo-router";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown:false,
        tabBarStyle:{
          backgroundColor:"#0f172a",
          borderTopColor:"#1e293b"
        },
        tabBarActiveTintColor:"#38bdf8",
        tabBarInactiveTintColor:"#64748b"
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title:"Home"
        }}
      />

        <Tabs.Screen
          name="monitor"
          options={{
            title:"Monitor"
          }}
        />

      <Tabs.Screen
        name="settings"
        options={{
          title:"Settings"
        }}
      />
    </Tabs>
  );
}
