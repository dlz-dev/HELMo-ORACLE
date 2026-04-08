"""
HELMo Oracle — Point d'entrée
"""

import dash

from callbacks import register_callbacks
from layout import INDEX_STRING, build_layout

# ── App ────────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__)
app.index_string = INDEX_STRING
app.layout       = build_layout()

register_callbacks(app)

# ── Lancement ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8050)