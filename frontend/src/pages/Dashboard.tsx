import React, { useState, useMemo } from "react";
import { useAuthStore } from "@/stores/authStore";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  ShoppingCart,
  TrendingUp,
  Package,
  Clock,
  ArrowUpRight,
  Download,
  RefreshCw,
  Info,
  Calendar,
} from "lucide-react";
import { Button, Modal, Chip, Badge } from "@/components/ui";
import { formatCurrency } from "@/lib/utils";
import { motion } from "framer-motion";

// Spending and Sales dataset variations
const mockDatasets: Record<string, { month: string; spend: number; refund: number }[]> = {
  "7d": [
    { month: "Mon", spend: 40, refund: 5 },
    { month: "Tue", spend: 95, refund: 10 },
    { month: "Wed", spend: 80, refund: 20 },
    { month: "Thu", spend: 140, refund: 15 },
    { month: "Fri", spend: 210, refund: 40 },
    { month: "Sat", spend: 160, refund: 10 },
    { month: "Sun", spend: 220, refund: 25 },
  ],
  "30d": [
    { month: "Week 1", spend: 450, refund: 30 },
    { month: "Week 2", spend: 620, refund: 50 },
    { month: "Week 3", spend: 580, refund: 40 },
    { month: "Week 4", spend: 710, refund: 90 },
  ],
  "12m": [
    { month: "Jan", spend: 120, refund: 10 },
    { month: "Feb", spend: 350, refund: 25 },
    { month: "Mar", spend: 210, refund: 15 },
    { month: "Apr", spend: 450, refund: 50 },
    { month: "May", spend: 600, refund: 45 },
    { month: "Jun", spend: 320, refund: 20 },
    { month: "Jul", spend: 510, refund: 35 },
    { month: "Aug", spend: 420, refund: 30 },
    { month: "Sep", spend: 680, refund: 70 },
    { month: "Oct", spend: 590, refund: 55 },
    { month: "Nov", spend: 820, refund: 90 },
    { month: "Dec", spend: 950, refund: 110 },
  ],
};

export const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const [timeRange, setTimeRange] = useState<"7d" | "30d" | "12m">("30d");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [drillDownMetric, setDrillDownMetric] = useState<string | null>(null);

  const activeData = useMemo(() => mockDatasets[timeRange], [timeRange]);

  // Aggregate totals
  const aggregates = useMemo(() => {
    const totalSpend = activeData.reduce((acc, curr) => acc + curr.spend, 0);
    const totalRefund = activeData.reduce((acc, curr) => acc + curr.refund, 0);
    const ordersCount = timeRange === "7d" ? 18 : timeRange === "30d" ? 64 : 842;
    const growth = timeRange === "7d" ? "+4.2%" : timeRange === "30d" ? "+14.8%" : "+28.4%";

    return {
      totalSpend,
      totalRefund,
      ordersCount,
      growth,
    };
  }, [activeData, timeRange]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      toast({
        title: "Metrics Synchronized",
        description: "Dashboard datasets updated in real-time.",
        variant: "success",
      });
    }, 800);
  };

  const handleExport = () => {
    const csvContent = "data:text/csv;charset=utf-8," 
      + ["Period,Spending,Refunds"].join(",") + "\n"
      + activeData.map(e => `${e.month},${e.spend},${e.refund}`).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `cloudscale-spending-${timeRange}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toast = ({ title, description, variant }: { title: string; description: string; variant: "success" }) => {
    console.log(`[Toast] ${title}: ${description} (${variant})`);
  };

  return (
    <div className="space-y-6">
      {/* Welcome segment */}
      <div className="relative overflow-hidden bg-gradient-to-r from-primary via-indigo-600 to-purple-600 p-8 rounded-3xl text-white shadow-xl">
        <div className="relative z-10">
          <h1 className="text-3xl font-extrabold tracking-tight">
            Welcome back, {user?.full_name || "Enterprise User"}!
          </h1>
          <p className="text-indigo-100 mt-2 text-sm max-w-xl">
            Monitor real-time checkout activities, system performance indicators, and commerce operations.
          </p>
        </div>
        <div className="absolute right-0 bottom-0 opacity-15 translate-y-12 translate-x-12">
          <TrendingUp className="h-64 w-64" />
        </div>
      </div>

      {/* Control Actions & Time range selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card border p-4 rounded-2xl shadow-sm">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Reporting Interval:</span>
          <div className="flex gap-1.5 ml-2">
            <Chip
              variant="interactive"
              selected={timeRange === "7d"}
              onSelect={() => setTimeRange("7d")}
            >
              7 Days
            </Chip>
            <Chip
              variant="interactive"
              selected={timeRange === "30d"}
              onSelect={() => setTimeRange("30d")}
            >
              30 Days
            </Chip>
            <Chip
              variant="interactive"
              selected={timeRange === "12m"}
              onSelect={() => setTimeRange("12m")}
            >
              12 Months
            </Chip>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />}
            onClick={handleRefresh}
          >
            Sync
          </Button>
          <Button
            variant="outline"
            size="sm"
            icon={<Download className="h-4 w-4" />}
            onClick={handleExport}
          >
            Export
          </Button>
        </div>
      </div>

      {/* KPI Stats Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          whileHover={{ y: -4 }}
          onClick={() => setDrillDownMetric("spending")}
          className="bg-card hover:bg-card/85 p-6 rounded-2xl border shadow-sm cursor-pointer transition-colors space-y-4"
        >
          <div className="flex justify-between items-start">
            <div className="p-3 bg-primary/10 text-primary rounded-xl">
              <ShoppingCart className="h-6 w-6" />
            </div>
            <Badge variant="success" icon={<ArrowUpRight className="h-3 w-3" />}>
              Active
            </Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Total Spending</p>
            <h3 className="text-3xl font-extrabold mt-1">
              {formatCurrency(aggregates.totalSpend)}
            </h3>
            <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
              <span className="text-green-500 font-semibold">{aggregates.growth}</span> vs previous period
            </p>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          onClick={() => setDrillDownMetric("orders")}
          className="bg-card hover:bg-card/85 p-6 rounded-2xl border shadow-sm cursor-pointer transition-colors space-y-4"
        >
          <div className="flex justify-between items-start">
            <div className="p-3 bg-green-500/10 text-green-500 rounded-xl">
              <Package className="h-6 w-6" />
            </div>
            <Badge variant="info">Healthy</Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Checkout Success</p>
            <h3 className="text-3xl font-extrabold mt-1">{aggregates.ordersCount}</h3>
            <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
              <span className="text-green-500 font-semibold">99.8%</span> SLA transaction success rate
            </p>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          onClick={() => setDrillDownMetric("refunds")}
          className="bg-card hover:bg-card/85 p-6 rounded-2xl border shadow-sm cursor-pointer transition-colors space-y-4"
        >
          <div className="flex justify-between items-start">
            <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
              <TrendingUp className="h-6 w-6" />
            </div>
            <Badge variant="warning">Controlled</Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Refund Deductions</p>
            <h3 className="text-3xl font-extrabold mt-1">
              {formatCurrency(aggregates.totalRefund)}
            </h3>
            <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
              <span className="text-amber-500 font-semibold">-{((aggregates.totalRefund / aggregates.totalSpend) * 100).toFixed(1)}%</span> from gross spend
            </p>
          </div>
        </motion.div>
      </div>

      {/* Main Charts & Activity Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spending area/bar chart */}
        <div className="lg:col-span-2 bg-card p-6 rounded-2xl border shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-foreground">Spending Trends</h3>
            <span className="text-xs text-muted-foreground font-semibold flex items-center gap-1">
              <Info className="h-3 w-3" /> Real-time active data
            </span>
          </div>

          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {timeRange === "7d" ? (
                <BarChart data={activeData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                  <XAxis dataKey="month" stroke="#9ca3af" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} axisLine={false} />
                  <ChartTooltip />
                  <Legend />
                  <Bar dataKey="spend" name="Spend" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="refund" name="Refund" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              ) : (
                <AreaChart data={activeData}>
                  <defs>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorRefund" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                  <XAxis dataKey="month" stroke="#9ca3af" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} axisLine={false} />
                  <ChartTooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="spend"
                    name="Spend"
                    stroke="hsl(var(--primary))"
                    fillOpacity={1}
                    fill="url(#colorSpend)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="refund"
                    name="Refund"
                    stroke="#f59e0b"
                    fillOpacity={1}
                    fill="url(#colorRefund)"
                    strokeWidth={2}
                  />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* Real-time event timeline */}
        <div className="bg-card p-6 rounded-2xl border shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-foreground mb-4">Operations Feed</h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-green-500/10 text-green-500 rounded-lg shrink-0">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Order completed successfully</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Order ID #20412 has reached terminal state.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary/10 text-primary rounded-lg shrink-0">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Catalog sync triggered</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Stock quantities rebalanced in central warehouse.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-yellow-500/10 text-yellow-500 rounded-lg shrink-0">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Saga checkpoint reached</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Payment credentials verified for shipping.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t pt-4 mt-6">
            <Button variant="outline" className="w-full text-xs">
              View All Operations
            </Button>
          </div>
        </div>
      </div>

      {/* Drill-down Modal details */}
      <Modal
        open={!!drillDownMetric}
        onClose={() => setDrillDownMetric(null)}
        title={`Metric Breakdown: ${drillDownMetric?.toUpperCase() || ""}`}
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Granular breakdown of the historical metric trends under reporting period ({timeRange}).
          </p>
          <div className="divide-y border rounded-xl overflow-hidden text-sm bg-card">
            {activeData.map((d, index) => (
              <div key={index} className="flex justify-between p-3">
                <span className="font-medium">{d.month}</span>
                <span className="font-mono text-primary font-bold">
                  {drillDownMetric === "spending"
                    ? formatCurrency(d.spend)
                    : drillDownMetric === "refunds"
                    ? formatCurrency(d.refund)
                    : Math.ceil(d.spend / 15)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Dashboard;
