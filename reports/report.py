import base64
from io import BytesIO
from datetime import datetime

import matplotlib.pyplot as plt


def fig_to_base64_png(fig):
    """
    Convert a matplotlib figure to a base64 PNG string for embedding in HTML.
    """
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64


def build_html_report(title, settings, metrics, figures):
    """
    settings: dict of strategy settings
    metrics: dict of key metrics
    figures: list of tuples [("Figure Title", matplotlib_fig), ...]
    Returns: HTML string
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Settings table
    settings_rows = ""
    for k, v in settings.items():
        settings_rows += f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"

    # Metrics table
    metrics_rows = ""
    for k, v in metrics.items():
        metrics_rows += f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"

    # Figures
    fig_blocks = ""
    for fig_title, fig in figures:
        img = fig_to_base64_png(fig)
        fig_blocks += f"""
        <h3 style="margin-top:24px;">{fig_title}</h3>
        <img src="data:image/png;base64,{img}" style="max-width:100%; border:1px solid #ddd; border-radius:8px;" />
        """

    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <title>{title}</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 24px;
          color: #111;
        }}
        h1 {{ margin-bottom: 0; }}
        .sub {{ color: #666; margin-top: 4px; }}
        table {{
          border-collapse: collapse;
          width: 100%;
          margin-top: 12px;
        }}
        td {{
          border: 1px solid #ddd;
          padding: 8px;
          vertical-align: top;
        }}
        .card {{
          border: 1px solid #ddd;
          border-radius: 10px;
          padding: 14px;
          margin-top: 16px;
        }}
      </style>
    </head>
    <body>
      <h1>{title}</h1>
      <div class="sub">Generated: {now}</div>

      <div class="card">
        <h2>Strategy Settings</h2>
        <table>
          {settings_rows}
        </table>
      </div>

      <div class="card">
        <h2>Key Metrics</h2>
        <table>
          {metrics_rows}
        </table>
      </div>

      <div class="card">
        <h2>Charts</h2>
        {fig_blocks}
      </div>
    </body>
    </html>
    """
    return html
