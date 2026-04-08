"""
HELMo Oracle — Callbacks & logique de données
"""

from collections import defaultdict
from datetime import datetime

import plotly.graph_objects as go
import requests
from dash import Input, Output, html

from config import API_URL, AXIS_STYLE, COLORS, GRAPH_LAYOUT, PROVIDER_COLORS


# ── Helpers : construction des figures ────────────────────────────────────────

def _empty_fig() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**GRAPH_LAYOUT)
    return fig


def _bar_fig(labels: list, values: list, color: str, height: int = 260) -> go.Figure:
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=color, marker_line_width=0))
    fig.update_layout(
        **GRAPH_LAYOUT, height=height, showlegend=False,
        xaxis=dict(tickvals=labels[::10], ticktext=labels[::10], **AXIS_STYLE),
        yaxis=dict(tickformat="d", **AXIS_STYLE),
    )
    return fig


def _pie_fig(labels: list, values: list, colors: list, height: int = 260,
             legend_pos: str = "v") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color=COLORS["bg"], width=2)),
        textfont=dict(family="DM Mono, monospace", size=11),
        hole=0.5,
    ))
    fig.update_layout(
        **GRAPH_LAYOUT, height=height, showlegend=True,
        legend=dict(orientation=legend_pos, x=1.0, y=0.5),
    )
    return fig


def _histogram_fig(data: list, height: int = 220) -> go.Figure:
    if not data:
        return _empty_fig()
    fig = go.Figure(go.Histogram(x=data, nbinsx=20,
                                 marker_color=COLORS["blue"], marker_line_width=0))
    fig.update_layout(
        **GRAPH_LAYOUT, height=height, showlegend=False,
        xaxis=dict(title="ms", **AXIS_STYLE),
        yaxis=AXIS_STYLE,
    )
    return fig


# ── Helpers : construction des composants HTML ────────────────────────────────

def _minute_buckets(events: list, now_ts: float) -> tuple[list, list]:
    """Retourne (labels, values) pour une timeline par minute sur 60 min."""
    buckets: dict[int, int] = defaultdict(int)
    for e in events:
        age_min = int((now_ts - e["ts"]) // 60)
        if 0 <= age_min < 60:
            buckets[age_min] += 1
    labels = [f"-{i}m" for i in range(59, -1, -1)]
    values = [buckets.get(i, 0) for i in range(59, -1, -1)]
    return labels, values


def _build_query_feed(events: list) -> list:
    items = []

    for e in events:
        # 1. Ignorer les événements qui n'ont pas de question
        question = e.get("question", "").strip()
        if not question:
            continue

        t = datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        source = e.get("source", "web")
        provider = e.get("provider", "")
        latency = e.get("latency_ms", 0)

        # 2. Construire la liste des badges dynamiquement
        badges = [
            html.Span(source, className=f"badge {source}", style={"marginRight": "6px"})
        ]

        # Ajouter le provider seulement s'il n'est pas vide
        if provider:
            badges.append(html.Span(provider, className="badge groq", style={"marginRight": "6px"}))

        # Ajouter la latence seulement si elle est supérieure à 0
        if latency > 0:
            badges.append(html.Span(f"{latency} ms",
                                    style={"fontSize": "10px", "color": COLORS["muted"],
                                           "fontFamily": "DM Mono, monospace"}))

        # 3. Assembler l'élément HTML
        items.append(html.Div([
            html.Span(t, className="feed-time"),
            html.Div([
                html.Div(badges),
                html.Div(question[:90], className="feed-question"),
            ]),
        ], className="feed-item"))

        # 4. S'arrêter quand on a 15 éléments valides
        if len(items) >= 15:
            break

    return items


def _build_services(db_ok: bool) -> list:
    services = [
        ("PostgreSQL + pgvector", db_ok, "Base de données vectorielle"),
        ("Redis Stream",          True,  "Monitoring temps réel"),
        ("Backend FastAPI",       True,  "API REST + RAG pipeline"),
    ]
    items = []
    for name, ok, desc in services:
        color = COLORS["green"] if ok else COLORS["red"]
        items.append(html.Div([
            html.Div([
                html.Span("●", style={"color": color, "marginRight": "8px", "fontSize": "14px"}),
                html.Span(name, style={"fontWeight": "500"}),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div(desc, style={"fontSize": "11px", "color": COLORS["muted"],
                                  "marginLeft": "22px", "fontFamily": "DM Mono, monospace"}),
        ], style={"padding": "12px 0", "borderBottom": f"1px solid {COLORS['border']}"}))
    return items


def _build_ingest_feed(ingest_events: list) -> list:
    _label_map = {
        "ingest_guardian": lambda e: (
            (COLORS["green"], "ACCEPTED") if e["status"] == "accepted"
            else (COLORS["red"], "REJECTED")
        ),
        "ingest_complete": lambda _: (COLORS["blue"], "DONE"),
    }
    items = []
    for e in ingest_events[:20]:
        t      = datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        etype  = e["type"]
        color, label = _label_map.get(etype, lambda _: (COLORS["red"], "ERROR"))(e)

        if etype == "ingest_guardian":
            detail = e.get("reason", "") or ""
        elif etype == "ingest_complete":
            detail = f"+{e.get('new_chunks', 0)} chunks"
        else:
            detail = e.get("error", "")

        items.append(html.Div([
            html.Span(t, className="feed-time"),
            html.Div([
                html.Span(label,
                          style={"color": color, "fontFamily": "DM Mono, monospace",
                                 "fontSize": "10px", "fontWeight": "600", "marginRight": "8px"}),
                html.Span(e.get("filename", ""), style={"fontSize": "12px", "marginRight": "8px"}),
                html.Span(detail, style={"fontSize": "11px", "color": COLORS["muted"],
                                         "fontFamily": "DM Mono, monospace"}),
            ]),
        ], className="feed-item"))
    return items


# ── Callback principal ────────────────────────────────────────────────────────

def register_callbacks(app) -> None:
    @app.callback(
        # Header
        Output("header-sub",   "children"),
        Output("header-badge", "children"),
        Output("header-badge", "className"),
        # KPIs requêtes
        Output("kpi-total",   "children"),
        Output("kpi-rpm",     "children"),
        Output("kpi-latency", "children"),
        Output("kpi-hour",    "children"),
        # Graphiques requêtes
        Output("graph-timeline",  "figure"),
        Output("graph-providers", "figure"),
        Output("graph-latency",   "figure"),
        # Feeds & services
        Output("live-feed",       "children"),
        Output("services-status", "children"),
        # KPIs ingestion
        Output("kpi-chunks",      "children"),
        Output("kpi-accepted",    "children"),
        Output("kpi-rejected",    "children"),
        Output("kpi-accept-rate", "children"),
        # Graphiques ingestion
        Output("graph-ingest-timeline", "figure"),
        Output("graph-guardian",        "figure"),
        Output("ingest-feed",           "children"),
        Input("live-interval", "n_intervals"),
    )
    def update_dashboard(_):
        now       = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        now_ts    = now.timestamp()

        # Valeurs de secours (hors-ligne / dégradé)
        _empty = _empty_fig()
        _fallback = (
            "—", "—", "—", "—",
            _empty, _empty, _empty,
            [], [],
            "—", "—", "—", "—",
            _empty, _empty, [],
        )

        # ── Récupération des métriques ────────────────────────────────────────
        try:
            r    = requests.get(f"{API_URL}/metrics", timeout=10)
            data = r.json()
        except Exception as exc:
            err = f"Erreur connexion : {exc}"
            return (err, "● Hors ligne", "status-badge error", *_fallback)

        if not data.get("available"):
            return ("Redis indisponible", "● Dégradé", "status-badge error", *_fallback)

        stats  = data["stats"]
        events = data["events"]

        header_sub = f"Dernière mise à jour : {timestamp} — {len(events)} events en mémoire"

        # ── Graphiques requêtes ───────────────────────────────────────────────
        t_labels, t_values = _minute_buckets(events, now_ts)
        fig_timeline = _bar_fig(t_labels, t_values, COLORS["blue"])

        provider_counts = defaultdict(int)
        for e in events:
            if e.get("type") == "chat":
                provider = e.get("provider")
                if provider and str(provider).strip() not in ["", "0", "unknown"]:
                    provider_counts[str(provider).strip()] += 1


        providers = list(provider_counts.keys())

        # Si on a au moins un provider valide, on génère le camembert, sinon graphique vide
        if providers:
            fig_providers = _pie_fig(
                labels=providers,
                values=[provider_counts[p] for p in providers],
                colors=PROVIDER_COLORS[:len(providers)],
            )
        else:
            fig_providers = _empty_fig()

        latencies  = [e["latency_ms"] for e in events if e.get("latency_ms", 0) > 0]
        fig_latency = _histogram_fig(latencies)

        # ── Feeds & services ──────────────────────────────────────────────────
        feed_items    = _build_query_feed(events)
        service_items = _build_services(stats.get("db_ok", False))

        # ── Ingestion ─────────────────────────────────────────────────────────
        ingest_events    = [e for e in events if e["type"].startswith("ingest_")]
        complete_events  = [e for e in ingest_events if e["type"] == "ingest_complete"]

        total_chunks  = stats.get("total_chunks_ingested", 0)
        accepted      = stats.get("files_accepted", 0)
        rejected      = stats.get("files_rejected", 0)
        total_guardian = accepted + rejected
        accept_rate   = f"{round(accepted / total_guardian * 100)}%" if total_guardian > 0 else "—"

        i_labels, i_values = _minute_buckets(complete_events, now_ts)
        fig_ingest_timeline = _bar_fig(i_labels, i_values, COLORS["green"])

        fig_guardian = _pie_fig(
            labels=["Acceptés", "Rejetés"],
            values=[accepted, rejected],
            colors=[COLORS["green"], COLORS["red"]],
        )

        ingest_feed = _build_ingest_feed(ingest_events)

        return (
            header_sub, "● Système actif", "status-badge",
            str(stats.get("total_queries",      "—")),
            str(stats.get("queries_last_minute","—")),
            f"{stats.get('avg_latency_ms', 0)} ms",
            str(stats.get("queries_last_hour",  "—")),
            fig_timeline, fig_providers, fig_latency,
            feed_items, service_items,
            str(total_chunks), str(accepted), str(rejected), accept_rate,
            fig_ingest_timeline, fig_guardian, ingest_feed,
        )