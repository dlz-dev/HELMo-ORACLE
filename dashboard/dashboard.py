"""
HELMo Oracle — Dashboard de monitoring temps réel
Affiche les métriques live du backend via Redis Stream + endpoint /metrics
"""

from collections import defaultdict
from datetime import datetime

import dash
import plotly.graph_objects as go
import requests
from dash import dcc, html, Input, Output

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = "https://api.dlzteam.com"

GRAPH_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0", family="DM Sans, sans-serif"),
    margin=dict(l=20, r=20, t=30, b=20),
)

# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__)

app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>HELMo Oracle — Live Monitor</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body, #react-entry-point, ._dash-loading, .dash-renderer { height: 100%; width: 100%; }
        body { background: #0f1117; font-family: "DM Sans", sans-serif; color: #e2e8f0; }

        .wrapper { display: flex; min-height: 100vh; width: 100%; }

        /* Sidebar */
        .sidebar {
            width: 220px; min-height: 100vh; background: #1a1d27;
            border-right: 1px solid #2a2d3e; display: flex; flex-direction: column;
            position: fixed; top: 0; left: 0; z-index: 100;
        }
        .sidebar-logo {
            padding: 20px; border-bottom: 1px solid #2a2d3e;
            font-size: 16px; font-weight: 600; text-decoration: none;
            color: #e2e8f0; display: block;
        }
        .sidebar-logo span { color: #6c63ff; }
        .sidebar-logo-sub { font-size: 10px; color: #8892a4; font-family: "DM Mono, monospace"; margin-top: 3px; }
        .sidebar-section {
            padding: 16px 12px 8px; font-size: 10px; color: #8892a4;
            letter-spacing: 1.5px; text-transform: uppercase; font-family: "DM Mono, monospace";
        }
        .sidebar-item {
            padding: 10px 20px; font-size: 13px; color: #8892a4; cursor: pointer;
            border-radius: 6px; margin: 2px 8px; display: flex; align-items: center;
            gap: 10px; text-decoration: none; transition: all 0.15s;
        }
        .sidebar-item:hover { background: #2a2d3e; color: #e2e8f0; }
        .sidebar-item.active { background: rgba(108,99,255,0.15); color: #6c63ff; border-left: 3px solid #6c63ff; }
        .sidebar-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
        .sidebar-footer {
            margin-top: auto; padding: 16px 20px; border-top: 1px solid #2a2d3e;
            font-size: 10px; color: #2a2d3e; font-family: "DM Mono, monospace"; line-height: 1.6;
        }

        /* Main */
        .main { margin-left: 220px; flex: 1; min-height: 100vh; display: flex; flex-direction: column; }

        /* Header */
        .header {
            padding: 16px 28px; border-bottom: 1px solid #2a2d3e;
            display: flex; justify-content: space-between; align-items: center;
            background: #1a1d27; position: sticky; top: 0; z-index: 99;
        }
        .header-title { font-size: 18px; font-weight: 600; }
        .header-sub { font-size: 11px; color: #8892a4; margin-top: 2px; font-family: "DM Mono, monospace"; }
        .status-badge {
            background: rgba(81,207,102,0.1); border: 1px solid rgba(81,207,102,0.25);
            color: #51cf66; padding: 6px 14px; border-radius: 20px;
            font-size: 11px; font-family: "DM Mono, monospace";
        }
        .status-badge.error {
            background: rgba(255,107,107,0.1); border-color: rgba(255,107,107,0.25); color: #ff6b6b;
        }

        /* Content */
        .content { padding: 24px 28px; flex: 1; }

        /* KPIs */
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px; }
        .kpi-card {
            background: #1a1d27; border: 1px solid #2a2d3e; border-radius: 8px;
            padding: 18px; position: relative; overflow: hidden;
        }
        .kpi-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
        .kpi-card.blue::before { background: #6c63ff; }
        .kpi-card.green::before { background: #51cf66; }
        .kpi-card.amber::before { background: #fcc419; }
        .kpi-card.red::before { background: #ff6b6b; }
        .kpi-label { font-size: 10px; color: #8892a4; text-transform: uppercase; letter-spacing: 1px; font-family: "DM Mono, monospace"; margin-bottom: 8px; }
        .kpi-value { font-size: 30px; font-weight: 600; line-height: 1; }
        .kpi-value.blue { color: #6c63ff; }
        .kpi-value.green { color: #51cf66; }
        .kpi-value.amber { color: #fcc419; }
        .kpi-value.red { color: #ff6b6b; }
        .kpi-sub { font-size: 10px; color: #8892a4; margin-top: 6px; font-family: "DM Mono, monospace"; }

        /* Charts */
        .charts-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
        .charts-grid-full { margin-bottom: 14px; }
        .chart-card { background: #1a1d27; border: 1px solid #2a2d3e; border-radius: 8px; padding: 18px; }
        .chart-title {
            font-size: 10px; color: #8892a4; letter-spacing: 1.5px; text-transform: uppercase;
            font-family: "DM Mono, monospace"; margin-bottom: 14px; padding-bottom: 12px;
            border-bottom: 1px solid #2a2d3e;
        }

        /* Feed */
        .feed-item {
            padding: 10px 0; border-bottom: 1px solid #1e2130;
            display: flex; align-items: flex-start; gap: 10px;
        }
        .feed-item:last-child { border-bottom: none; }
        .feed-time { font-size: 10px; color: #8892a4; font-family: "DM Mono, monospace"; white-space: nowrap; padding-top: 2px; }
        .feed-question { font-size: 12px; color: #e2e8f0; line-height: 1.5; }

        /* Badge */
        .badge {
            padding: 3px 8px; border-radius: 4px; font-size: 10px;
            font-family: "DM Mono, monospace"; display: inline-block; white-space: nowrap;
        }
        .badge.web { background: rgba(108,99,255,0.15); color: #6c63ff; border: 1px solid rgba(108,99,255,0.3); }
        .badge.discord { background: rgba(88,101,242,0.15); color: #5865f2; border: 1px solid rgba(88,101,242,0.3); }

        /* Provider badge */
        .badge.groq { background: rgba(81,207,102,0.1); color: #51cf66; border: 1px solid rgba(81,207,102,0.3); }
        .badge.openai { background: rgba(252,196,25,0.1); color: #fcc419; border: 1px solid rgba(252,196,25,0.3); }

        /* Latency bar */
        .latency-bar-wrap { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
        .latency-bar { height: 4px; border-radius: 2px; background: #6c63ff; transition: width 0.5s; }

        html { scroll-behavior: smooth; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''

app.layout = html.Div([
    dcc.Interval(id="live-interval", interval=10000, n_intervals=0),

    html.Div([

        # Sidebar
        html.Div([
            html.A([
                html.Div([html.Span("HELMo "), html.Span("Oracle", style={"color": "#6c63ff"})]),
                html.Div("Live Monitor", className="sidebar-logo-sub"),
            ], href="#", className="sidebar-logo"),

            html.Div("Vue d'ensemble", className="sidebar-section"),
            html.A([html.Div(className="sidebar-dot"), "Dashboard"], href="#section-kpis", className="sidebar-item active"),

            html.Div("Activité", className="sidebar-section"),
            html.A([html.Div(className="sidebar-dot"), "Timeline"], href="#section-timeline", className="sidebar-item"),
            html.A([html.Div(className="sidebar-dot"), "Questions"], href="#section-feed", className="sidebar-item"),

            html.Div("Ingestion", className="sidebar-section"),
            html.A([html.Div(className="sidebar-dot"), "Pipeline"], href="#section-ingest", className="sidebar-item"),
            html.A([html.Div(className="sidebar-dot"), "Guardian"], href="#section-ingest", className="sidebar-item"),

            html.Div("Système", className="sidebar-section"),
            html.A([html.Div(className="sidebar-dot"), "Services"], href="#section-services", className="sidebar-item"),

            html.Div([
                "HELMo Oracle v1.0",
                html.Br(),
                "Monitoring — 2026",
            ], className="sidebar-footer"),
        ], className="sidebar"),

        # Main
        html.Div([

            # Header
            html.Div([
                html.Div([
                    html.Div("Live Monitor", className="header-title"),
                    html.Div(id="header-sub", children="Connexion...", className="header-sub"),
                ]),
                html.Div(id="header-badge", children="● Connexion...", className="status-badge"),
            ], className="header"),

            # Content
            html.Div([

                # KPIs
                html.Div([
                    html.Div([
                        html.Div("Requêtes totales", className="kpi-label"),
                        html.Div(id="kpi-total", children="—", className="kpi-value blue"),
                        html.Div("depuis le démarrage", className="kpi-sub"),
                    ], className="kpi-card blue"),
                    html.Div([
                        html.Div("Dernière minute", className="kpi-label"),
                        html.Div(id="kpi-rpm", children="—", className="kpi-value green"),
                        html.Div("requêtes / min", className="kpi-sub"),
                    ], className="kpi-card green"),
                    html.Div([
                        html.Div("Latence moyenne", className="kpi-label"),
                        html.Div(id="kpi-latency", children="—", className="kpi-value amber"),
                        html.Div("millisecondes (RAG end-to-end)", className="kpi-sub"),
                    ], className="kpi-card amber"),
                    html.Div([
                        html.Div("Dernière heure", className="kpi-label"),
                        html.Div(id="kpi-hour", children="—", className="kpi-value blue"),
                        html.Div("requêtes / heure", className="kpi-sub"),
                    ], className="kpi-card blue"),
                ], className="kpi-grid", id="section-kpis"),

                # Timeline + provider breakdown
                html.Div([
                    html.Div([
                        html.Div("Activité — dernière heure (par minute)", className="chart-title"),
                        dcc.Graph(id="graph-timeline", config={"displayModeBar": False}),
                    ], className="chart-card"),
                    html.Div([
                        html.Div("Répartition par provider LLM", className="chart-title"),
                        dcc.Graph(id="graph-providers", config={"displayModeBar": False}),
                    ], className="chart-card"),
                ], className="charts-grid-2 section-anchor", id="section-timeline"),

                # Latency histogram
                html.Div([
                    html.Div([
                        html.Div("Distribution des latences RAG (ms)", className="chart-title"),
                        dcc.Graph(id="graph-latency", config={"displayModeBar": False}),
                    ], className="chart-card"),
                ], className="charts-grid-full"),

                # Feed
                html.Div([
                    html.Div([
                        html.Div("Dernières questions posées", className="chart-title"),
                        html.Div(id="live-feed"),
                    ], className="chart-card"),
                    html.Div([
                        html.Div("Statut des services", className="chart-title"),
                        html.Div(id="services-status"),
                    ], className="chart-card"),
                ], className="charts-grid-2 section-anchor", id="section-feed"),

                # Section Ingestion KPIs
                html.Div([
                    html.Div([
                        html.Div("Chunks ingérés", className="kpi-label"),
                        html.Div(id="kpi-chunks", children="—", className="kpi-value blue"),
                        html.Div("vecteurs dans la base", className="kpi-sub"),
                    ], className="kpi-card blue"),
                    html.Div([
                        html.Div("Fichiers acceptés", className="kpi-label"),
                        html.Div(id="kpi-accepted", children="—", className="kpi-value green"),
                        html.Div("par le Guardian", className="kpi-sub"),
                    ], className="kpi-card green"),
                    html.Div([
                        html.Div("Fichiers rejetés", className="kpi-label"),
                        html.Div(id="kpi-rejected", children="—", className="kpi-value red"),
                        html.Div("hors scope", className="kpi-sub"),
                    ], className="kpi-card red"),
                    html.Div([
                        html.Div("Taux d'acceptation", className="kpi-label"),
                        html.Div(id="kpi-accept-rate", children="—", className="kpi-value amber"),
                        html.Div("Guardian accuracy", className="kpi-sub"),
                    ], className="kpi-card amber"),
                ], className="kpi-grid section-anchor", id="section-ingest"),

                # Section Ingestion charts
                html.Div([
                    html.Div([
                        html.Div("Fichiers ingérés — timeline", className="chart-title"),
                        dcc.Graph(id="graph-ingest-timeline", config={"displayModeBar": False}),
                    ], className="chart-card"),
                    html.Div([
                        html.Div("Guardian — décisions", className="chart-title"),
                        dcc.Graph(id="graph-guardian", config={"displayModeBar": False}),
                    ], className="chart-card"),
                ], className="charts-grid-2"),

                # Feed ingestion
                html.Div([
                    html.Div([
                        html.Div("Log d'ingestion en temps réel", className="chart-title"),
                        html.Div(id="ingest-feed"),
                    ], className="chart-card"),
                ], className="charts-grid-full"),

            ], className="content"),
        ], className="main"),

    ], className="wrapper"),
])


# ── Callback principal ────────────────────────────────────────────────────────
@app.callback(
    Output("header-sub", "children"),
    Output("header-badge", "children"),
    Output("header-badge", "className"),
    Output("kpi-total", "children"),
    Output("kpi-rpm", "children"),
    Output("kpi-latency", "children"),
    Output("kpi-hour", "children"),
    Output("graph-timeline", "figure"),
    Output("graph-providers", "figure"),
    Output("graph-latency", "figure"),
    Output("live-feed", "children"),
    Output("services-status", "children"),
    Output("kpi-chunks", "children"),
    Output("kpi-accepted", "children"),
    Output("kpi-rejected", "children"),
    Output("kpi-accept-rate", "children"),
    Output("graph-ingest-timeline", "figure"),
    Output("graph-guardian", "figure"),
    Output("ingest-feed", "children"),
    Input("live-interval", "n_intervals"),
)
def update_dashboard(_):
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S")

    empty_fig = go.Figure()
    empty_fig.update_layout(**GRAPH_LAYOUT)
    empty_outputs = ["—"] * 4 + [empty_fig] * 2 + [[]]

    try:
        r = requests.get(f"{API_URL}/metrics", timeout=10)
        data = r.json()
    except Exception as e:
        err = f"Erreur connexion : {e}"
        return err, "● Hors ligne", "status-badge error", "—", "—", "—", "—", empty_fig, empty_fig, empty_fig, [], [], *empty_outputs

    if not data.get("available"):
        return "Redis indisponible", "● Dégradé", "status-badge error", "—", "—", "—", "—", empty_fig, empty_fig, empty_fig, [], [], *empty_outputs

    stats = data["stats"]
    events = data["events"]

    header_sub = f"Dernière mise à jour : {timestamp} — {len(events)} events en mémoire"
    badge_txt = "● Système actif"
    badge_cls = "status-badge"

    # ── Timeline par minute ──────────────────────────────────────────────────
    buckets = defaultdict(int)
    now_ts = now.timestamp()
    for e in events:
        age_min = int((now_ts - e["ts"]) // 60)
        if 0 <= age_min < 60:
            buckets[age_min] += 1

    labels = [f"-{i}m" for i in range(59, -1, -1)]
    values = [buckets.get(i, 0) for i in range(59, -1, -1)]
    fig_timeline = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color="#6c63ff", marker_line_width=0,
    ))
    fig_timeline.update_layout(
        **GRAPH_LAYOUT, height=260, showlegend=False,
        xaxis=dict(tickvals=labels[::10], ticktext=labels[::10], gridcolor="#2a2d3e"),
        yaxis=dict(gridcolor="#2a2d3e", tickformat="d"),
    )

    # ── Répartition providers ────────────────────────────────────────────────
    provider_counts = defaultdict(int)
    for e in events:
        provider_counts[e.get("provider", "unknown")] += 1
    providers = list(provider_counts.keys())
    p_values = [provider_counts[p] for p in providers]
    colors = ["#6c63ff", "#51cf66", "#fcc419", "#ff6b6b", "#5865f2"]
    fig_providers = go.Figure(go.Pie(
        labels=providers, values=p_values,
        marker=dict(colors=colors[:len(providers)], line=dict(color="#0f1117", width=2)),
        textfont=dict(family="DM Mono, monospace", size=11),
        hole=0.5,
    ))
    fig_providers.update_layout(**GRAPH_LAYOUT, height=260, showlegend=True,
                                legend=dict(orientation="v", x=1.0, y=0.5))

    # ── Distribution latences ────────────────────────────────────────────────
    latencies = [e["latency_ms"] for e in events if e.get("latency_ms", 0) > 0]
    if latencies:
        fig_latency = go.Figure(go.Histogram(
            x=latencies, nbinsx=20,
            marker_color="#6c63ff", marker_line_width=0,
        ))
    else:
        fig_latency = go.Figure()
    fig_latency.update_layout(
        **GRAPH_LAYOUT, height=220, showlegend=False,
        xaxis=dict(title="ms", gridcolor="#2a2d3e"),
        yaxis=dict(gridcolor="#2a2d3e"),
    )

    # ── Feed questions ───────────────────────────────────────────────────────
    feed_items = []
    for e in events[:15]:
        t = datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        source = e.get("source", "web")
        provider = e.get("provider", "")
        latency = e.get("latency_ms", 0)
        question = e.get("question", "")[:90]

        feed_items.append(html.Div([
            html.Span(t, className="feed-time"),
            html.Div([
                html.Div([
                    html.Span(source, className=f"badge {source}", style={"marginRight": "6px"}),
                    html.Span(provider, className="badge groq", style={"marginRight": "6px"}),
                    html.Span(f"{latency} ms", style={"fontSize": "10px", "color": "#8892a4", "fontFamily": "DM Mono, monospace"}),
                ]),
                html.Div(question, className="feed-question"),
            ]),
        ], className="feed-item"))

    # ── Services ─────────────────────────────────────────────────────────────
    db_ok = stats.get("db_ok", False)
    services = [
        ("PostgreSQL + pgvector", db_ok, "Base de données vectorielle"),
        ("Redis Stream", True, "Monitoring temps réel"),
        ("Backend FastAPI", True, "API REST + RAG pipeline"),
    ]
    service_items = []
    for name, ok, desc in services:
        color = "#51cf66" if ok else "#ff6b6b"
        label = "OK" if ok else "ERR"
        service_items.append(html.Div([
            html.Div([
                html.Span("●", style={"color": color, "marginRight": "8px", "fontSize": "14px"}),
                html.Span(name, style={"fontWeight": "500"}),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div(desc, style={"fontSize": "11px", "color": "#8892a4", "marginLeft": "22px", "fontFamily": "DM Mono, monospace"}),
        ], style={"padding": "12px 0", "borderBottom": "1px solid #1e2130"}))

    # ── Ingestion ────────────────────────────────────────────────────────────────
    ingest_events = [e for e in events if e["type"].startswith("ingest_")]
    complete_events = [e for e in ingest_events if e["type"] == "ingest_complete"]
    guardian_events = [e for e in ingest_events if e["type"] == "ingest_guardian"]

    total_chunks = stats.get("total_chunks_ingested", 0)
    accepted = stats.get("files_accepted", 0)
    rejected = stats.get("files_rejected", 0)
    total_guardian = accepted + rejected
    accept_rate = f"{round(accepted / total_guardian * 100)}%" if total_guardian > 0 else "—"

    # Timeline ingestion
    ingest_buckets = defaultdict(int)
    for e in complete_events:
        age_min = int((now_ts - e["ts"]) // 60)
        if 0 <= age_min < 60:
            ingest_buckets[age_min] += 1
    i_labels = [f"-{i}m" for i in range(59, -1, -1)]
    i_values = [ingest_buckets.get(i, 0) for i in range(59, -1, -1)]
    fig_ingest_timeline = go.Figure(go.Bar(x=i_labels, y=i_values, marker_color="#51cf66", marker_line_width=0))
    fig_ingest_timeline.update_layout(**GRAPH_LAYOUT, height=260, showlegend=False,
                                      xaxis=dict(tickvals=i_labels[::10], ticktext=i_labels[::10], gridcolor="#2a2d3e"),
                                      yaxis=dict(gridcolor="#2a2d3e", tickformat="d"))

    # Guardian pie
    fig_guardian = go.Figure(go.Pie(
        labels=["Acceptés", "Rejetés"],
        values=[accepted, rejected],
        marker=dict(colors=["#51cf66", "#ff6b6b"], line=dict(color="#0f1117", width=2)),
        hole=0.5,
        textfont=dict(family="DM Mono, monospace", size=11),
    ))
    fig_guardian.update_layout(**GRAPH_LAYOUT, height=260)

    # Feed ingestion
    ingest_feed = []
    for e in ingest_events[:20]:
        t = datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        if e["type"] == "ingest_guardian":
            color = "#51cf66" if e["status"] == "accepted" else "#ff6b6b"
            label = "ACCEPTED" if e["status"] == "accepted" else "REJECTED"
            detail = e.get("reason", "") or ""
        elif e["type"] == "ingest_complete":
            color = "#6c63ff"
            label = "DONE"
            detail = f"+{e.get('new_chunks', 0)} chunks"
        else:
            color = "#ff6b6b"
            label = "ERROR"
            detail = e.get("error", "")

        ingest_feed.append(html.Div([
            html.Span(t, className="feed-time"),
            html.Div([
                html.Span(label, style={"color": color, "fontFamily": "DM Mono, monospace",
                                        "fontSize": "10px", "fontWeight": "600", "marginRight": "8px"}),
                html.Span(e.get("filename", ""), style={"fontSize": "12px", "marginRight": "8px"}),
                html.Span(detail, style={"fontSize": "11px", "color": "#8892a4", "fontFamily": "DM Mono, monospace"}),
            ]),
        ], className="feed-item"))

    return (
        header_sub, badge_txt, badge_cls,
        str(stats.get("total_queries", "—")),
        str(stats.get("queries_last_minute", "—")),
        f"{stats.get('avg_latency_ms', 0)} ms",
        str(stats.get("queries_last_hour", "—")),
        fig_timeline, fig_providers, fig_latency,
        feed_items, service_items,
        str(total_chunks), str(accepted), str(rejected), accept_rate,
        fig_ingest_timeline, fig_guardian, ingest_feed,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8050)
