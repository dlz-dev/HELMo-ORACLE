"use client";

import { useEffect, useState } from "react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import { Activity, Users, Clock, Zap, RefreshCw, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface MetricsData {
  available: boolean;
  stats: {
    total_queries?: number;
    avg_latency_ms?: number;
    total_chunks_ingested?: number;
    total_users?: number;
    db_ok?: boolean;
  };
  events: any[];
}

export function DashboardSection({
  onMetricsUpdate,
}: {
  onMetricsUpdate?: (stats: any) => void;
}) {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [mounted, setMounted] = useState(false);

  const fetchMetrics = async () => {
    try {
      const res = await fetch("/api/admin/metrics");
      if (res.ok) {
        const json = await res.json();
        setData(json);
        if (onMetricsUpdate && json.stats) {
          onMetricsUpdate(json.stats);
        }
      }
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    fetchMetrics();
    if (!autoRefresh) return;
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-[var(--gold)]" />
      </div>
    );
  }

  if (!data) return null;

  const { stats, events } = data;

  // Préparation des données pour le graphique de timeline
  const timelineData = events
    .filter((e) => e.type === "chat")
    .slice(0, 20)
    .reverse()
    .map((e) => ({
      time: new Date(e.ts * 1000).toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      latency: e.latency_ms,
    }));

  // Calcul répartition providers
  const providerDataMap: Record<string, number> = {};
  events.forEach((e) => {
    if (e.type === "chat" && e.provider) {
      providerDataMap[e.provider] = (providerDataMap[e.provider] || 0) + 1;
    }
  });
  const providerData = Object.entries(providerDataMap).map(([name, value]) => ({
    name,
    value,
  }));

  const COLORS = ["#c9a84c", "#e2c06a", "#8892a4", "#4b5563"];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header avec bouton refresh */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h2 className="text-lg font-semibold text-[var(--text)]">
            Performance du Système
          </h2>
          <p className="text-xs text-[var(--text-subtle)]">
            Vue d'ensemble de l'activité de votre Oracle
          </p>
        </div>
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-medium transition-all uppercase tracking-wider",
            autoRefresh
              ? "bg-[var(--gold-glow)] text-[var(--gold)] border border-[var(--gold)]/20"
              : "bg-[var(--bg-subtle)] text-[var(--text-subtle)] border border-[var(--border)]",
          )}
        >
          <div
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              autoRefresh
                ? "bg-[var(--gold)] animate-pulse"
                : "bg-[var(--text-subtle)]",
            )}
          />
          {autoRefresh ? "Live Monitoring" : "Monitoring en pause"}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Requêtes"
          value={stats.total_queries?.toLocaleString() || "0"}
          subValue="Toutes sessions confondues"
          icon={Activity}
        />
        <MetricCard
          title="Latence Moyenne"
          value={`${stats.avg_latency_ms || 0} ms`}
          subValue="Temps de réponse serveur"
          icon={Zap}
        />
        <MetricCard
          title="Utilisateurs"
          value={stats.total_users || 0}
          subValue="Comptes enregistrés"
          icon={Users}
        />
        <MetricCard
          title="Archives indexées"
          value={stats.total_chunks_ingested?.toLocaleString() || "0"}
          subValue="Documents uniques en base"
          icon={Search}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graphique Latence */}
        <Card className="lg:col-span-2 border-[var(--border)] bg-[var(--surface)] shadow-sm">
          <CardHeader className="pb-2 border-b border-[var(--border)] bg-[var(--bg-subtle)]/50">
            <CardTitle className="text-xs font-semibold uppercase tracking-widest text-[var(--text-subtle)] flex items-center gap-2">
              <Clock size={14} className="text-[var(--gold)]" />
              Évolution de la latence (ms)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div
              className="h-[240px] min-h-[240px] w-full"
              style={{ position: "relative" }}
            >
              {mounted && (
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <LineChart data={timelineData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="time"
                      stroke="var(--text-subtle)"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="var(--text-subtle)"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `${value}ms`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      itemStyle={{ color: "var(--gold)" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="latency"
                      stroke="var(--gold)"
                      strokeWidth={2}
                      dot={{ fill: "var(--gold)", strokeWidth: 2, r: 3 }}
                      activeDot={{ r: 5, strokeWidth: 0 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Répartition Providers */}
        <Card className="border-[var(--border)] bg-[var(--surface)] shadow-sm">
          <CardHeader className="pb-2 border-b border-[var(--border)] bg-[var(--bg-subtle)]/50">
            <CardTitle className="text-xs font-semibold uppercase tracking-widest text-[var(--text-subtle)] flex items-center gap-2">
              <Users size={14} className="text-[var(--gold)]" />
              Intelligence Artificielle
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div
              className="h-[240px] min-h-[240px] w-full"
              style={{ position: "relative" }}
            >
              {mounted && (
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <PieChart>
                    <Pie
                      data={providerData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {providerData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="mt-4 space-y-2">
              {providerData.map((p, i) => (
                <div
                  key={p.name}
                  className="flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2 text-[var(--text-muted)]">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: COLORS[i % COLORS.length] }}
                    />
                    <span className="capitalize">{p.name}</span>
                  </div>
                  <span className="font-medium text-[var(--text)]">
                    {p.value}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subValue,
  icon: Icon,
}: {
  title: string;
  value: string | number;
  subValue: string;
  icon: any;
}) {
  return (
    <Card className="border-[var(--border)] bg-[var(--surface)] hover:border-[var(--gold)]/20 transition-all group shadow-sm">
      <CardContent className="pt-5 px-5 pb-4">
        <div className="flex items-start justify-between mb-2">
          <div className="p-2 rounded-lg bg-[var(--bg-subtle)] group-hover:bg-[var(--gold-glow)] transition-colors">
            <Icon
              size={18}
              className="text-[var(--text-subtle)] group-hover:text-[var(--gold)] transition-colors"
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--text-subtle)] font-semibold mb-1">
            {title}
          </p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-2xl font-bold text-[var(--text)] tracking-tight">
              {value}
            </h3>
          </div>
          <p className="text-[10px] text-[var(--text-muted)] mt-1 truncate">
            {subValue}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
