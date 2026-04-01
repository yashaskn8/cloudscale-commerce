import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ShieldCheck, Cpu, Database, Activity } from "lucide-react";

// Mock system load dataset
const metricsData = [
  { time: "12:00", cpu: 20, kafka: 5 },
  { time: "13:00", cpu: 45, kafka: 15 },
  { time: "14:00", cpu: 32, kafka: 10 },
  { time: "15:00", cpu: 85, kafka: 55 },
  { time: "16:00", cpu: 55, kafka: 30 },
  { time: "17:00", cpu: 40, kafka: 12 },
];

export const AdminDashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin Operations</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time monitor of microservice queues, caches, and cluster loads
          </p>
        </div>
      </div>

      {/* KPI Stats widgets */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm flex items-center">
          <div className="p-3 bg-primary/10 text-primary rounded-xl mr-4">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase">EKS Node CPU</p>
            <h3 className="text-2xl font-bold dark:text-white mt-1">38%</h3>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm flex items-center">
          <div className="p-3 bg-blue-500/10 text-blue-500 rounded-xl mr-4">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase">Postgres Pools</p>
            <h3 className="text-2xl font-bold dark:text-white mt-1">12 / 60</h3>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm flex items-center">
          <div className="p-3 bg-orange-500/10 text-orange-500 rounded-xl mr-4">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase">Kafka Queue Lag</p>
            <h3 className="text-2xl font-bold dark:text-white mt-1">0 msg</h3>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm flex items-center">
          <div className="p-3 bg-green-500/10 text-green-500 rounded-xl mr-4">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-semibold uppercase">Service Health</p>
            <h3 className="text-2xl font-bold dark:text-white mt-1">100%</h3>
          </div>
        </div>
      </div>

      {/* Cluster load chart */}
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Kubernetes Pod Performance</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={metricsData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="cpu" name="Node CPU (%)" stroke="hsl(var(--primary))" strokeWidth={2} />
              <Line type="monotone" dataKey="kafka" name="Kafka Lag (k)" stroke="#f97316" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
export default AdminDashboard;
