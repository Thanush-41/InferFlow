import { useState, useEffect } from 'react';
import { Activity, Clock, AlertTriangle, Zap, Database, Users } from 'lucide-react';
import { getDashboardMetrics, getLatencyData, getProviderStats, getErrors, getThroughput, DashboardMetrics, ProviderStats, LatencyBucket } from '../api';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [providers, setProviders] = useState<ProviderStats[]>([]);
  const [latency, setLatency] = useState<LatencyBucket[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
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
      setMetrics(m);
      setProviders(p);
      setLatency(l);
      setErrors(e);
      setThroughput(t);
    } catch (err) {
      console.error('Failed to fetch dashboard data', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [timeWindow]);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <div className="flex gap-2">
          {[1, 6, 24, 72].map((h) => (
            <button
              key={h}
              onClick={() => setTimeWindow(h)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                timeWindow === h ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'
              }`}
            >
              {h}h
            </button>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            icon={<Activity size={18} />}
            label="Total Requests"
            value={metrics.total_requests.toString()}
            color="blue"
          />
          <MetricCard
            icon={<Clock size={18} />}
            label="Avg Latency"
            value={`${metrics.avg_latency_ms.toFixed(0)}ms`}
            sub={`P95: ${metrics.p95_latency_ms.toFixed(0)}ms`}
            color="green"
          />
          <MetricCard
            icon={<AlertTriangle size={18} />}
            label="Error Rate"
            value={`${metrics.error_rate.toFixed(1)}%`}
            color={metrics.error_rate > 5 ? 'red' : 'green'}
          />
          <MetricCard
            icon={<Zap size={18} />}
            label="Throughput"
            value={`${metrics.requests_per_minute.toFixed(1)}/min`}
            color="purple"
          />
          <MetricCard
            icon={<Database size={18} />}
            label="Total Tokens"
            value={formatNumber(metrics.total_tokens)}
            color="yellow"
          />
          <MetricCard
            icon={<Users size={18} />}
            label="Active Sessions"
            value={metrics.active_conversations.toString()}
            color="cyan"
          />
          <MetricCard
            icon={<Clock size={18} />}
            label="P99 Latency"
            value={`${metrics.p99_latency_ms.toFixed(0)}ms`}
            color="orange"
          />
          <MetricCard
            icon={<Activity size={18} />}
            label="RPM"
            value={metrics.requests_per_minute.toFixed(2)}
            color="indigo"
          />
        </div>
      )}

      {/* Provider Stats */}
      {providers.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Provider Performance</h2>
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="text-left p-3">Provider</th>
                  <th className="text-left p-3">Model</th>
                  <th className="text-right p-3">Requests</th>
                  <th className="text-right p-3">Avg Latency</th>
                  <th className="text-right p-3">Errors</th>
                  <th className="text-right p-3">Tokens</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="p-3 font-medium">{p.provider}</td>
                    <td className="p-3 text-slate-300">{p.model}</td>
                    <td className="p-3 text-right">{p.total_requests}</td>
                    <td className="p-3 text-right">{p.avg_latency_ms.toFixed(0)}ms</td>
                    <td className="p-3 text-right text-red-400">{p.error_count}</td>
                    <td className="p-3 text-right">{formatNumber(p.total_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Latency Chart (simple bar representation) */}
      {latency.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Latency Over Time</h2>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
            <div className="flex items-end gap-1 h-32">
              {latency.slice(-30).map((bucket, i) => {
                const maxLatency = Math.max(...latency.map(b => b.avg_latency_ms));
                const height = maxLatency > 0 ? (bucket.avg_latency_ms / maxLatency) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-blue-500/60 hover:bg-blue-400/80 rounded-t transition-colors cursor-pointer"
                    style={{ height: `${height}%`, minHeight: '2px' }}
                    title={`${bucket.avg_latency_ms.toFixed(0)}ms (${bucket.request_count} req)`}
                  />
                );
              })}
            </div>
            <p className="text-xs text-slate-500 mt-2">Last {latency.slice(-30).length} buckets</p>
          </div>
        </div>
      )}

      {/* Throughput Chart */}
      {throughput.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Throughput Over Time</h2>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
            <div className="flex items-end gap-1 h-32">
              {throughput.slice(-30).map((bucket: any, i: number) => {
                const maxReq = Math.max(...throughput.map((b: any) => b.requests));
                const height = maxReq > 0 ? (bucket.requests / maxReq) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-green-500/60 hover:bg-green-400/80 rounded-t transition-colors cursor-pointer"
                    style={{ height: `${height}%`, minHeight: '2px' }}
                    title={`${bucket.requests} requests`}
                  />
                );
              })}
            </div>
            <p className="text-xs text-slate-500 mt-2">Requests per 5-min bucket</p>
          </div>
        </div>
      )}

      {/* Recent Errors */}
      {errors.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Recent Errors</h2>
          <div className="space-y-2">
            {errors.slice(0, 10).map((err: any) => (
              <div key={err.id} className="bg-red-900/20 border border-red-800/30 rounded-lg p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-red-300">{err.error_message}</p>
                    <p className="text-xs text-slate-400 mt-1">{err.provider}/{err.model}</p>
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(err.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
    cyan: 'text-cyan-400',
    orange: 'text-orange-400',
    indigo: 'text-indigo-400',
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-4">
      <div className={`flex items-center gap-2 mb-2 ${colorMap[color] || 'text-slate-400'}`}>
        {icon}
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <p className="text-xl font-bold">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}
