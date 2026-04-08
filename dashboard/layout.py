"""
HELMo Oracle — Mise en page (layout + index_string)
"""

from dash import dcc, html

# ── HTML shell ─────────────────────────────────────────────────────────────────
INDEX_STRING = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>HELMo Oracle — Live Monitor</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''


# ── Composants réutilisables ───────────────────────────────────────────────────

def _sidebar_link(label: str, href: str, active: bool = False) -> html.A:
    cls = "sidebar-item active" if active else "sidebar-item"
    return html.A([html.Div(className="sidebar-dot"), label], href=href, className=cls)


def _kpi_card(kpi_id: str, label: str, sub: str, color: str) -> html.Div:
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(id=kpi_id, children="—", className=f"kpi-value {color}"),
        html.Div(sub, className="kpi-sub"),
    ], className=f"kpi-card {color}")


def _chart_card(title: str, *children) -> html.Div:
    return html.Div([html.Div(title, className="chart-title"), *children], className="chart-card")


# ── Layout principal ───────────────────────────────────────────────────────────

def build_layout() -> html.Div:
    return html.Div([
        dcc.Interval(id="live-interval", interval=10_000, n_intervals=0),

        html.Div([

            # ── Sidebar ──────────────────────────────────────────────────────
            html.Div([
                html.A([
                    html.Div([html.Span("HELMo "), html.Span("Oracle", style={"color": "#6c63ff"})]),
                    html.Div("Live Monitor", className="sidebar-logo-sub"),
                ], href="#", className="sidebar-logo"),

                html.Div("Vue d'ensemble", className="sidebar-section"),
                _sidebar_link("Dashboard", "#section-kpis", active=True),

                html.Div("Activité", className="sidebar-section"),
                _sidebar_link("Timeline",  "#section-timeline"),
                _sidebar_link("Questions", "#section-feed"),

                html.Div("Ingestion", className="sidebar-section"),
                _sidebar_link("Pipeline", "#section-ingest"),
                _sidebar_link("Guardian", "#section-ingest"),

                html.Div("Système", className="sidebar-section"),
                _sidebar_link("Services", "#section-services"),

                html.Div(["HELMo Oracle v1.0", html.Br(), "Monitoring — 2026"],
                         className="sidebar-footer"),
            ], className="sidebar"),

            # ── Main ─────────────────────────────────────────────────────────
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

                    # ── KPIs requêtes ─────────────────────────────────────
                    html.Div([
                        _kpi_card("kpi-total",   "Requêtes totales",  "depuis le démarrage",          "blue"),
                        _kpi_card("kpi-rpm",     "Dernière minute",   "requêtes / min",               "green"),
                        _kpi_card("kpi-latency", "Latence moyenne",   "millisecondes (RAG end-to-end)","amber"),
                        _kpi_card("kpi-hour",    "Dernière heure",    "requêtes / heure",             "blue"),
                    ], className="kpi-grid", id="section-kpis"),

                    # ── Timeline + providers ──────────────────────────────
                    html.Div([
                        _chart_card(
                            "Activité — dernière heure (par minute)",
                            dcc.Graph(id="graph-timeline", config={"displayModeBar": False}),
                        ),
                        _chart_card(
                            "Répartition par provider LLM",
                            dcc.Graph(id="graph-providers", config={"displayModeBar": False}),
                        ),
                    ], className="charts-grid-2 section-anchor", id="section-timeline"),

                    # ── Histogramme latences ──────────────────────────────
                    html.Div([
                        _chart_card(
                            "Distribution des latences RAG (ms)",
                            dcc.Graph(id="graph-latency", config={"displayModeBar": False}),
                        ),
                    ], className="charts-grid-full"),

                    # ── Feed questions + statut services ──────────────────
                    html.Div([
                        _chart_card("Dernières questions posées", html.Div(id="live-feed")),
                        _chart_card("Statut des services",        html.Div(id="services-status")),
                    ], className="charts-grid-2 section-anchor", id="section-feed"),

                    # ── KPIs ingestion ────────────────────────────────────
                    html.Div([
                        _kpi_card("kpi-chunks",      "Chunks ingérés",      "vecteurs dans la base", "blue"),
                        _kpi_card("kpi-accepted",    "Fichiers acceptés",   "par le Guardian",       "green"),
                        _kpi_card("kpi-rejected",    "Fichiers rejetés",    "hors scope",            "red"),
                        _kpi_card("kpi-accept-rate", "Taux d'acceptation",  "Guardian accuracy",     "amber"),
                    ], className="kpi-grid section-anchor", id="section-ingest"),

                    # ── Charts ingestion ──────────────────────────────────
                    html.Div([
                        _chart_card(
                            "Fichiers ingérés — timeline",
                            dcc.Graph(id="graph-ingest-timeline", config={"displayModeBar": False}),
                        ),
                        _chart_card(
                            "Guardian — décisions",
                            dcc.Graph(id="graph-guardian", config={"displayModeBar": False}),
                        ),
                    ], className="charts-grid-2"),

                    # ── Feed ingestion ────────────────────────────────────
                    html.Div([
                        _chart_card("Log d'ingestion en temps réel", html.Div(id="ingest-feed")),
                    ], className="charts-grid-full"),

                ], className="content"),
            ], className="main"),

        ], className="wrapper"),
    ])