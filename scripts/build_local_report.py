# ruff: noqa: E501
"""Build a self-contained HTML report from the local curated context mart."""

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from functions.shared.config import settings

INK = "#172a2a"
MUTED = "#536663"
PAPER = "#f4f4ed"
GREEN = "#176b55"
CORAL = "#c4553d"
GOLD = "#bc8b2c"
BLUE = "#437d91"


def _base_layout(figure: go.Figure, title: str, height: int = 390) -> go.Figure:
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Georgia, serif", "color": INK, "size": 12},
        margin={"l": 54, "r": 28, "t": 66, "b": 48},
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.22, "x": 0},
    )
    figure.update_xaxes(showgrid=False, linecolor="#c7cec4", tickfont={"color": MUTED})
    figure.update_yaxes(gridcolor="#dde1d8", zerolinecolor="#c7cec4", tickfont={"color": MUTED})
    return figure


def _fx_figure(data: pd.DataFrame) -> go.Figure:
    rates = data.dropna(subset=["average_usd_lkr"])
    rates = rates.drop_duplicates("month_date").sort_values("month_date")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=rates["month_date"],
            y=rates["average_usd_lkr"],
            name="Average LKR per USD",
            mode="lines",
            line={"color": GREEN, "width": 2.5},
            fill="tozeroy",
            fillcolor="rgba(23,107,85,0.08)",
        )
    )
    figure.update_yaxes(title="LKR per USD")
    return _base_layout(figure, "01 / Exchange-rate history")


def _weather_figure(data: pd.DataFrame) -> go.Figure:
    colors = [GREEN, CORAL, BLUE, GOLD, "#6e7353", "#9b6b52"]
    figure = go.Figure()
    locations = sorted(data["location_key"].dropna().unique())
    for index, location in enumerate(locations):
        rows = data.loc[data["location_key"].eq(location)].dropna(subset=["total_rainfall_mm"])
        monthly = rows.drop_duplicates("month_date").sort_values("month_date")
        figure.add_trace(
            go.Scatter(
                x=monthly["month_date"],
                y=monthly["total_rainfall_mm"],
                name=location.replace("_", " ").title(),
                mode="lines",
                line={"color": colors[index % len(colors)], "width": 1.8},
                visible=True,
            )
        )
    buttons = [
        {
            "label": "All locations",
            "method": "update",
            "args": [{"visible": [True] * len(locations)}],
        }
    ]
    for selected_index, location in enumerate(locations):
        visibility = [index == selected_index for index in range(len(locations))]
        buttons.append(
            {
                "label": location.replace("_", " ").title(),
                "method": "update",
                "args": [{"visible": visibility}],
            }
        )
    figure.update_layout(
        updatemenus=[
            {
                "type": "dropdown",
                "direction": "down",
                "x": 1,
                "xanchor": "right",
                "y": 1.18,
                "buttons": buttons,
                "bgcolor": PAPER,
                "bordercolor": "#c7cec4",
            }
        ]
    )
    figure.update_yaxes(title="Rainfall (mm/month)")
    return _base_layout(figure, "02 / Rainfall by destination")


def _arrivals_figure(data: pd.DataFrame) -> go.Figure:
    report_rows = data.loc[data["arrivals_coverage_status"].eq("top_ten_source_markets_only")]
    if report_rows.empty:
        return _base_layout(go.Figure(), "03 / Parsed source markets")
    monthly = report_rows.groupby("month_date", as_index=False).first().sort_values("month_date")
    figure = go.Figure()
    regions = [
        ("parsed_top_market_asia_pacific_arrivals", "Asia & Pacific", GREEN),
        ("parsed_top_market_europe_arrivals", "Europe", CORAL),
        ("parsed_top_market_americas_arrivals", "Americas", BLUE),
        ("parsed_top_market_unmapped_arrivals", "Unmapped", GOLD),
    ]
    for column, label, color in regions:
        if column in monthly:
            figure.add_trace(
                go.Bar(x=monthly["month_date"], y=monthly[column], name=label, marker_color=color)
            )
    figure.update_layout(barmode="stack")
    figure.update_yaxes(title="Parsed arrivals (top-ten table only)")
    return _base_layout(figure, "03 / Parsed source-market mix")


def _coverage_figure(data: pd.DataFrame) -> go.Figure:
    months = (
        data.loc[data["parsed_market_count"].notna()].groupby("month_date", as_index=False).first()
    )
    figure = go.Figure(
        go.Bar(
            x=months["month_date"],
            y=months["parsed_market_count"],
            marker_color=CORAL,
            text=months["arrivals_coverage_status"],
            hovertemplate="%{x|%b %Y}<br>%{y} parsed markets<extra></extra>",
        )
    )
    figure.update_yaxes(title="Markets extracted")
    return _base_layout(figure, "04 / Arrivals source coverage", height=330)


def build_local_report(
    mart_path: Path, output_path: Path, dq_results_path: Path | None = None
) -> Path:
    data = pd.read_parquet(mart_path)
    data["month_date"] = pd.to_datetime(data["month_date"])
    data["arrivals_coverage_status"] = data["arrivals_coverage_status"].fillna(
        "no_parsed_market_rows"
    )
    fx_rows = data.dropna(subset=["average_usd_lkr"]).drop_duplicates("month_date")
    weather_rows = data.dropna(subset=["total_rainfall_mm"])
    report_rows = data.loc[data["arrivals_coverage_status"].eq("top_ten_source_markets_only")]
    parsed_arrivals = int(
        report_rows.groupby("month_date")["parsed_top_market_arrivals"].first().sum()
    )
    report_count = int(report_rows["month_date"].nunique())
    location_count = int(weather_rows["location_key"].nunique())
    date_span = (
        f"{data['month_date'].min():%b %Y} to {data['month_date'].max():%b %Y}"
        if not data.empty
        else "No data"
    )

    if dq_results_path is not None and dq_results_path.exists():
        dq = pd.read_parquet(dq_results_path)
        dq_summary = dq.loc[~dq["passed"]].copy()
        dq_table = (
            dq_summary[["dataset", "rule_id", "severity", "rows_failed"]].to_html(
                index=False, border=0, classes="health-table"
            )
            if not dq_summary.empty
            else "<p>All executed DQ rules passed.</p>"
        )
    else:
        dq_table = "<p>DQ checks have not been run for this local output.</p>"
    charts = [
        _fx_figure(data),
        _weather_figure(data),
        _arrivals_figure(data),
        _coverage_figure(data),
    ]
    plot_divs = []
    for index, chart in enumerate(charts):
        plot_divs.append(
            chart.to_html(
                full_html=False,
                include_plotlyjs=True if index == 0 else False,
                config={"responsive": True, "displaylogo": False},
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LankaPulse | Tourism &amp; Economy Observatory</title>
<style>
:root{{--paper:{PAPER};--ink:{INK};--muted:{MUTED};--green:{GREEN};--coral:{CORAL};--rule:#c7cec4}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:Georgia,'Times New Roman',serif}}
.masthead{{padding:30px clamp(20px,5vw,76px) 25px;border-bottom:1px solid var(--rule);background:linear-gradient(115deg,#e5e9dd 0%,var(--paper) 60%,#e9ddd2 100%)}}
.kicker{{font:700 11px/1.2 'Trebuchet MS',sans-serif;letter-spacing:1.6px;text-transform:uppercase;color:var(--green)}}
h1{{font-size:clamp(34px,5vw,64px);font-weight:500;line-height:.98;margin:14px 0 12px;max-width:900px}}
.intro{{font:15px/1.6 'Trebuchet MS',sans-serif;color:var(--muted);max-width:820px;margin:0}}
.meta{{display:flex;gap:22px;flex-wrap:wrap;margin-top:20px;font:12px 'Trebuchet MS',sans-serif;color:var(--muted)}}
main{{max-width:1440px;margin:auto;padding:28px clamp(16px,4vw,60px) 60px}}
.stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);margin-bottom:26px}}
.stat{{padding:18px 16px 20px 0;border-right:1px solid var(--rule)}}.stat:not(:first-child){{padding-left:20px}}.stat:last-child{{border:0}}
.stat b{{display:block;font-size:30px;font-weight:500;color:var(--green)}}.stat span{{display:block;margin-top:5px;font:11px/1.4 'Trebuchet MS',sans-serif;color:var(--muted);text-transform:uppercase}}
.warning{{border-left:4px solid var(--coral);padding:13px 16px;background:#f1e7de;font:13px/1.6 'Trebuchet MS',sans-serif;margin:0 0 26px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px 26px}}
.panel{{min-width:0;border-top:1px solid var(--rule);padding-top:4px}}
.notes{{margin-top:30px;border-top:2px solid var(--ink);padding-top:17px;display:grid;grid-template-columns:1fr 1fr;gap:24px;font:12px/1.65 'Trebuchet MS',sans-serif;color:var(--muted)}}
.notes h2{{font:500 19px Georgia,serif;color:var(--ink);margin:0 0 8px}}
footer{{padding:17px clamp(20px,5vw,76px);border-top:1px solid var(--rule);font:11px 'Trebuchet MS',sans-serif;color:var(--muted)}}
@media(max-width:780px){{.stats{{grid-template-columns:1fr 1fr}}.stat:nth-child(2){{border-right:0}}.stat:nth-child(3){{padding-left:0;border-top:1px solid var(--rule)}}.stat:nth-child(4){{border-top:1px solid var(--rule)}}.grid,.notes{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="masthead">
    <div class="kicker">LankaPulse / Local data edition</div>
    <h1>Tourism &amp; Economy<br>Observatory</h1>
    <p class="intro">A monthly view across exchange rates, destination weather, and the SLTDA source-market reports currently parsed in this project.</p>
    <div class="meta"><span>Window: {date_span}</span><span>Generated: {date.today().isoformat()}</span><span>Data: local backfill, not Azure-hosted</span></div>
</header>
<main>
    <section class="stats" aria-label="Dataset coverage">
        <div class="stat"><b>{len(fx_rows):,}</b><span>FX monthly observations / 56 currencies in source</span></div>
        <div class="stat"><b>{len(weather_rows):,}</b><span>Weather month-location observations / {location_count} locations</span></div>
        <div class="stat"><b>{parsed_arrivals:,}</b><span>Parsed top-market arrivals / {report_count} reports</span></div>
        <div class="stat"><b>{int((~data["arrivals_is_complete"].fillna(False)).sum()):,}</b><span>Mart rows not representing complete arrivals</span></div>
    </section>
    <aside class="warning"><strong>Coverage note:</strong> The available SLTDA PDFs currently contribute top-ten source-market tables only. These parsed values are not total tourist arrivals, and no complete country-level series or reconciliation is claimed.</aside>
    <section class="grid" aria-label="Tourism and economy charts">
        <div class="panel">{plot_divs[0]}</div>
        <div class="panel">{plot_divs[1]}</div>
        <div class="panel">{plot_divs[2]}</div>
        <div class="panel">{plot_divs[3]}</div>
    </section>
    <section class="notes">
        <div><h2>Reading the data</h2>FX is shown as Sri Lankan rupees per one US dollar. Rainfall totals are monthly sums for each selected location. The SLTDA chart visualizes only the markets extracted from each report's top-ten table; gaps mean there is no parsed report for that month.</div>
            <div><h2>Data health</h2>{dq_table}</div>
        <div><h2>Sources &amp; method</h2>Exchange rates: CBSL via Frankfurter. Weather: Open-Meteo historical archive, CC BY 4.0. Tourism: Sri Lanka Tourism Development Authority monthly PDFs. Correlation is descriptive and does not establish causation.</div>
    </section>
</main>
<footer>Local analytical preview • Generated from the curated Parquet mart • Weather data by Open-Meteo.com</footer>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mart",
        type=Path,
        default=settings.curated_root / "monthly_tourism_context.parquet",
    )
    parser.add_argument("--output", type=Path, default=Path("powerbi/local_report.html"))
    parser.add_argument("--dq-results", type=Path, default=Path("data/ops/dq_results.parquet"))
    args = parser.parse_args()
    print(build_local_report(args.mart, args.output, args.dq_results))


if __name__ == "__main__":
    main()
