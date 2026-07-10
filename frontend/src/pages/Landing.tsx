import React from "react";
import { Link } from "react-router";
import { motion } from "framer-motion";
import {
  Zap,
  Shield,
  ArrowRight,
  Sparkles,
  GitBranch,
  Terminal,
  Activity,
  Cpu,
  Workflow,
  Globe,
} from "lucide-react";

// ── Animation Configs ─────────────────────────────────────────────────────────
const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, ease: [0.2, 0.8, 0.2, 1] },
  },
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const floatAnimation = {
  animate: {
    y: [0, -12, 0],
    transition: {
      duration: 6,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

// ── Feature Definitions ────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: Workflow,
    title: "Choreographed Sagas",
    detail: "Event-driven checkout transactions with automated database compensatory rollback paths over Apache Kafka.",
    color: "from-emerald-400 to-teal-500",
    shadow: "shadow-emerald-500/20",
  },
  {
    icon: Shield,
    title: "RLS Tenant Isolation",
    detail: "Data partition boundaries secured at the database row level via session-scoped PostgreSQL client policies.",
    color: "from-indigo-400 to-blue-500",
    shadow: "shadow-indigo-500/20",
  },
  {
    icon: Cpu,
    title: "TF-IDF Vector Search",
    detail: "High-performance semantic query matching and recommendations built with dense float matrix cosine similarities.",
    color: "from-purple-400 to-violet-500",
    shadow: "shadow-purple-500/20",
  },
  {
    icon: Terminal,
    title: "Developer-First APIs",
    detail: "Fully typed OpenAPI schemas, gRPC service communication channels, and centralized Prometheus counters.",
    color: "from-pink-400 to-rose-500",
    shadow: "shadow-pink-500/20",
  },
];

export const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#060610] text-[#e7e0ed] font-sans relative overflow-hidden select-none">
      
      {/* ── Ambient Background Lighting ────────────────────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-5%] w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[130px]" />
        <div className="absolute top-[30%] right-[-10%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-[-10%] left-[20%] w-[500px] h-[500px] bg-emerald-600/5 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_20%,#060610_90%)]" />
      </div>

      <div className="relative z-10">
        {/* ── Navigation Header ──────────────────────────────────────────────────── */}
        <header className="sticky top-0 w-full h-18 bg-[#15121b]/40 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 md:px-12 z-50">
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">CloudScale Commerce</span>
          </Link>
          <div className="flex items-center space-x-4">
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-semibold text-gray-300 hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/login"
              className="px-4 py-2 text-sm font-semibold bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:shadow-lg hover:shadow-purple-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              Launch App
            </Link>
          </div>
        </header>

        {/* ── Hero Section ──────────────────────────────────────────────────────── */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 pt-20 md:pt-32 pb-16 text-center space-y-8 flex flex-col items-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="space-y-4 max-w-4xl"
          >
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-semibold text-purple-300">
              <Sparkles className="h-3.5 w-3.5 animate-pulse" />
              Next-Gen E-Commerce Architecture
            </div>
            <h1 className="text-4xl md:text-7xl font-extrabold text-white tracking-tight leading-[1.1] text-transparent bg-clip-text bg-gradient-to-b from-white via-white to-purple-200">
              Scale Your Commerce <br />
              <span className="bg-clip-text bg-gradient-to-r from-purple-400 via-indigo-400 to-emerald-400">
                to Hyper-Drive
              </span>
            </h1>
            <p className="text-lg md:text-xl text-gray-400 max-w-3xl mx-auto leading-relaxed pt-2">
              Orchestrate event-driven microservices with multi-tenant row-level security
              isolation and dense vector similarity search at sub-millisecond latencies.
            </p>
          </motion.div>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.6 }}
            className="flex flex-col sm:flex-row items-center gap-4 justify-center"
          >
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-bold rounded-lg shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2 group"
            >
              Get Started Free
              <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto px-8 py-3.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold rounded-lg hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              View Documentation
            </a>
          </motion.div>

          {/* ── Showcase Frame ───────────────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            variants={floatAnimation}
            className="w-full max-w-5xl pt-16"
          >
            <div className="relative glass-panel rounded-2xl overflow-hidden border border-white/10 shadow-[0_0_50px_rgba(139,92,246,0.15)]">
              {/* Window Bar */}
              <div className="h-10 bg-white/5 border-b border-white/5 flex items-center px-4 space-x-2">
                <div className="h-3 w-3 rounded-full bg-rose-500/80" />
                <div className="h-3 w-3 rounded-full bg-amber-500/80" />
                <div className="h-3 w-3 rounded-full bg-emerald-500/80" />
                <div className="flex-1 text-center text-xs text-gray-500 font-mono">
                  console.cloudscale-commerce.io
                </div>
              </div>
              {/* Mock Screen Content */}
              <div className="p-6 md:p-8 bg-[#0b0c16]/90 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                {/* Stats */}
                <div className="bg-[#171825]/60 border border-white/5 rounded-xl p-5 space-y-4">
                  <div className="flex justify-between items-center text-xs font-semibold text-gray-400">
                    <span>SAGA METRICS</span>
                    <span className="text-emerald-400 flex items-center gap-1">
                      <Activity className="h-3 w-3 animate-pulse" /> LIVE
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-3xl font-extrabold text-white font-mono">99.98%</p>
                    <p className="text-xs text-gray-500">Checkout Success Rate</p>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full w-[99.98%] bg-emerald-500 shadow-[0_0_8px_#10b981]" />
                  </div>
                </div>

                {/* Kafka Logs */}
                <div className="bg-[#171825]/60 border border-white/5 rounded-xl p-5 space-y-3 font-mono text-xs md:col-span-2">
                  <div className="text-gray-400 font-bold flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-purple-400" />
                    KAFKA EVENT LOGSTREAM
                  </div>
                  <div className="space-y-1.5 text-gray-500">
                    <p><span className="text-emerald-400">✓</span> [order-service] OrderCreatedEvent published (ID: ord_8829)</p>
                    <p><span className="text-emerald-400">✓</span> [payment-service] PaymentProcessedEvent published ($49.00)</p>
                    <p><span className="text-emerald-400">✓</span> [inventory-svc] StockReservedEvent published (Qty: 2)</p>
                    <p><span className="text-purple-400">⚡</span> [saga-orchestrator] Checkout transaction finalized in 450ms</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </section>

        {/* ── Feature Section ────────────────────────────────────────────────────── */}
        <section className="max-w-7xl mx-auto px-6 md:px-12 py-24 space-y-16">
          <div className="text-center space-y-3">
            <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight">
              Built for Enterprise Performance
            </h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              Hardened patterns delivering maximum security, durability, and response times.
            </p>
          </div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            {FEATURES.map((item, idx) => {
              const Icon = item.icon;
              return (
                <motion.div
                  key={idx}
                  variants={fadeUp}
                  whileHover={{ y: -8, transition: { duration: 0.2 } }}
                  className="glass-panel hover:border-white/20 p-8 rounded-xl relative overflow-hidden group shadow-lg transition-all duration-300"
                >
                  <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-white/20 via-white/5 to-transparent" />
                  <div className="flex gap-4">
                    <div className={`h-12 w-12 rounded-lg bg-gradient-to-br ${item.color} flex items-center justify-center shrink-0 shadow-lg ${item.shadow}`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold text-white group-hover:text-purple-300 transition-colors">
                        {item.title}
                      </h3>
                      <p className="text-gray-400 text-sm leading-relaxed">
                        {item.detail}
                      </p>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </section>

        {/* ── Footer ────────────────────────────────────────────────────────────── */}
        <footer className="w-full py-12 border-t border-white/5 text-center text-xs text-gray-500 bg-[#0b0c16]/50">
          <p>© 2026 CloudScale Commerce. Built with React 19, FastAPI, Kafka, and OpenTelemetry.</p>
        </footer>
      </div>
    </div>
  );
};

export default Landing;
