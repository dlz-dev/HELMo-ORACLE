"""
HELMo Oracle — Configuration centralisée
"""

import os
API_URL = os.environ.get("API_URL", "https://api.dlzteam.com")

# ── Couleurs ───────────────────────────────────────────────────────────────────
COLORS = {
    "blue":    "#6c63ff",
    "green":   "#51cf66",
    "amber":   "#fcc419",
    "red":     "#ff6b6b",
    "discord": "#5865f2",
    "bg":      "#0f1117",
    "surface": "#1a1d27",
    "border":  "#2a2d3e",
    "muted":   "#8892a4",
    "text":    "#e2e8f0",
}

PROVIDER_COLORS = [
    COLORS["blue"],
    COLORS["green"],
    COLORS["amber"],
    COLORS["red"],
    COLORS["discord"],
]

# ── Layout commun pour tous les graphiques Plotly ──────────────────────────────
GRAPH_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text"], family="DM Sans, sans-serif"),
    margin=dict(l=20, r=20, t=30, b=20),
)

AXIS_STYLE = dict(gridcolor=COLORS["border"])