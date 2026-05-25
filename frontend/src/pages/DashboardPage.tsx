import { useState, useEffect } from "react";
import {
  Activity, Clock, AlertTriangle, Zap, Database, Users, TrendingUp, Gauge,
} from "lucide-react";
import {
  getDashboardMetrics, getLatencyData, getProviderStats, getErrors,
  getThroughput, DashboardMetrics, ProviderStats, LatencyBucket,
} from "../api";

export default function DashboardPage() {
  const [metrics,    setMetrics]    = useState<DashboardMetrics | null>(null);
  const [providers,  setProviders]  = useState<ProviderStats[]>([]);
  const [latency,    setLatency]    = useState<LatencyBucket[]>([]);
  const [errors,     setErrors]     = useState<any[]>([]);
  const [throughput, setThroughput] = useState<any[]>([]);
  const [timeWindow, setTimeWindow] = useState(24);

  const fetchData = async () => {
    try {
      const [m, p, l, e, t] = await Promise.all([
        getDashboardMetrics(timeWindow),
        getProviderStats(timeWindow),
        getLatencyData(timeWindow),
        getErrors(timeWindow),
        getThroughput(timeWindow),
      ]);
      setMetrics(m); setProviders(p); setLatency(l); setErrors(e); setThroughput(t);
    } catch (err) { console.error("Dashboard fetch failed", err); }
  };

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 10_000);
    return () => clearInterval(t);
  }, [timeWindow]);

  return (
    <div className="h-full overflow-y-auto bg-[#0d0f17]">
      <div className="max-w-5xl mx-auto px-5 py-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-[15px] font-semibold text-slate-100">Dashboard</h1>
            <p className="text-[12px] text-slate-500 mt-0.5">Live inference observability</p>
          </div>
          <div className="flex items-center gap-1.5 bg-[#161921] border border-[#252836] rounded-xl p-1">
            {[1, 6, 24, 72].map((h) => (
              <button
                key={h}
                onClick={() => setTimeWindow(h)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
                  timeWindow === h
                    ? "bg-blue-600 text-white shadow-sm shadow-blue-900/50"
                    : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>

        {/* Metric cards */}
        {metrics && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <MetricCard icon={Activity}      label="Total Requests"  value={metrics.total_requests.toString()}                   accent="blue"   />
            <MetricCard icon={Clock}         label="Avg Latency"     value={`${metrics.avg_latency_ms.toFixed(0)}ms`}            sub={`P95 · ${metrics.p95_latency_ms.toFixed(0)}ms`} accent="violet" />
            <MetricCard icon={AlertTriangle} label="Error Rate"      value={`${metrics.error_rate.toFixed(1)}%`}                 accent={metrics.error_rate > 5 ? "red" : "emerald"} />
            <MetricCard icon={Zap}           label="Throughput"      value={`${metrics.requests_per_minute.toFixed(1)}/min`}     accent="amber"  />
            <MetricCard icon={Database}      label="Total Tokens"    value={fmt(metrics.total_tokens)}                          accent="cyan"   />
            <MetricCard icon={Users}         label="Active Sessions" value={metrics.active_conversations.toString()}             accent="indigo" />
            <MetricCard icon={Gauge}         label="P99 Latency"     value={`${metrics.p99_latency_ms.toFixed(0)}ms`}           accent="orange" />
            <MetricCard icon={TrendingUp}    label="RPM"             value={metrics.requests_per_minute.toFixed(2)}             accent="teal"   />
          </div>
        )}

        {/* Provider table */}
        {providers.length > 0 && (
          <Section title="Provider Performance" className="mb-6">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-[#252836]">
                    {["Provider", "Model", "Requests", "Avg Latency", "Errors", "Tokens"].map((h, i) => (
                      <th key={h} className={`py-2.5 px-3 font-semibold text-slate-500 uppercase tracking-wider text-[10px] ${i > 1 ? "text-right" : "text-left"}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {providers.map((p, i) => (
                    <tr key={i} className="border-b border-[#1e2130] hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                          <span className="font-medium text-slate-200">{p.provider}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-400 font-mono text-[11px]">{p.model}</td>
                      <td className="py-3 px-3 text-right text-slate-300">{p.total_requests}</td>
                      <td className="py-3 px-3 text-right text-slate-300">{p.avg_latency_ms.toFixed(0)}ms</td>
                      <td className="py-3 px-3 text-right">
                        <span className={p.error_count > 0 ? "text-red-400 font-medium" : "text-slate-500"}>
                          {p.error_count}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">{fmt(p.total_tokens)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {latency.length > 0 && (
            <Section title="Latency Over Time" subtitle="avg ms · 5-min buckets">
              <BarChart
                data={latency.slice(-24).map((b) => ({ value: b.avg_latency_ms, label: `${b.avg_latency_ms.toFixed(0)}ms`, sub: `${b.request_count} req` }))}
                color="blue"
              />
            </Section>
          )}
          {throughput.length > 0 && (
            <Section title="Throughput" subtitle="requests · 5-min buckets">
              <BarChart
                data={throughput.slice(-24).map((b: any) => ({ value: b.requests, label: `${b.requests}`, sub: "req" }))}
                color="emerald"
              />
            </Section>
          )}
        </div>

        {/* Recent errors */}
        {errors.length > 0 && (
          <Section title="Recent Errors">
            <div className="space-y-2">
              {errors.slice(0, 8).map((err: any) => (
                <div key={err.id} className="flex items-start gap-3 p-3 rounded-xl bg-red-950/20 border border-red-900/30">
                  <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-red-300 truncate">{err.error_message}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{err.provider} / {err.model}</p>
                  </div>
                  <span className="text-[10px] text-slate-600 flex-shrink-0 font-mono">
                    {new Date(err.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────

const ACCENT: Record<string, { icon: string; bar: string; glow: string }> = {
  blue:    { icon: "text-blue-400",    bar: "bg-blue-500",    glow: "shadow-blue-900/40"  },
  violet:  { icon: "text-violet-400",  bar: "bg-violet-500",  glow: "shadow-violet-900/40"},
  emerald: { icon: "text-emerald-400", bar: "bg-emerald-500", glow: "shadow-emerald-900/40"},
  red:     { icon: "text-red-400",     bar: "bg-red-500",     glow: "shadow-red-900/40"   },
  amber:   { icon: "text-amber-400",   bar: "bg-amber-500",   glow: "shadow-amber-900/40" },
  cyan:    { icon: "text-cyan-400",    bar: "bg-cyan-500",    glow: "shadow-cyan-900/40"  },
  indigo:  { icon: "text-indigo-400",  bar: "bg-indigo-500",  glow: "shadow-indigo-900/40"},
  orange:  { icon: "text-orange-400",  bar: "bg-orange-500",  glow: "shadow-orange-900/40"},
  teal:    { icon: "text-teal-400",    bar: "bg-teal-500",    glow: "shadow-teal-900/40"  },
};

function MetricCard({
  icon: Icon, label, value, sub, accent,
}: { icon: React.ElementType; label: string; value: string; sub?: string; accent: string }) {
  const a = ACCENT[accent] ?? ACCENT.blue;
  return (
    <div className="bg-[#161921] border border-[#252836] rounded-2xl p-4 hover:border-[#2e3147] transition-colors">
      <div className={`flex items-center gap-2 mb-3 ${a.icon}`}>
        <Icon size={15} />
        <span className="text-[11px] text-slate-500 font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-[22px] font-bold text-slate-100 tracking-tight leading-none">{value}</p>
      {sub && <p className="text-[11px] text-slate-600 mt-1.5">{sub}</p>}
    </div>
  );
}

function Section({
  title, subtitle, children, className = "",
}: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[#161921] border border-[#252836] rounded-2xl p-4 ${className}`}>
      <div className="flex items-baseline gap-2 mb-4">
        <h2 className="text-[13px] font-semibold text-slate-200">{title}</h2>
        {subtitle && <span className="text-[11px] text-slate-600">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function BarChart({
  data, color,
}: { data: { value: number; label: string; sub: string }[]; color: string }) {
  const a = ACCENT[color] ?? ACCENT.blue;
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div>
      <div className="flex items-end gap-0.5 h-28">
        {data.map((d, i) => {
          const pct = (d.value / max) * 100;
          return (
            <div key={i} className="group flex-1 flex flex-col justify-end relative">
              {/* Tooltip */}
              <div className="absolute bottom-full mb-1.5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="bg-[#1c1f2e] border border-[#2e3147] rounded-lg px-2 py-1.5 text-center whitespace-nowrap shadow-xl">
                  <p className="text-[11px] font-semibold text-slate-200">{d.label}</p>
                  <p className="text-[10px] text-slate-500">{d.sub}</p>
                </div>
              </div>
              <div
                className={`w-full ${a.bar} rounded-t opacity-70 group-hover:opacity-100 transition-all duration-150`}
                style={{ height: `${Math.max(pct, 2)}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-2">
        <span className="text-[10px] text-slate-700">oldest</span>
        <span className="text-[10px] text-slate-700">latest</span>
      </div>
    </div>
  );
}

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}
