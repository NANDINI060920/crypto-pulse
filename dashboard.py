"""
dashboard.py
------------
Streamlit dashboard for CryptoPulse. Run with:

    streamlit run dashboard.py

Visual identity: a dark trading-terminal look (deep navy, amber accent,
monospace numerals) rather than a default light SaaS-card dashboard --
grounded in what this project actually is: a live financial data feed.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from anomaly import isolation_forest_flags, rolling_zscore
from storage import fetch_history, init_db, list_tracked_coins

# ---- design tokens -------------------------------------------------------

BG = "#0D1321"
SURFACE = "#131A2A"
BORDER = "#232C42"
TEXT_PRIMARY = "#E7EAF2"
TEXT_SECONDARY = "#7C859C"
AMBER = "#E8A33D"
POSITIVE = "#3DDC97"
NEGATIVE = "#F2545B"

TICKER_SYMBOLS = {
    "bitcoin": "₿",
    "ethereum": "Ξ",
    "solana": "◎",
    "dogecoin": "Ð",
    "cardano": "₳",
}

st.set_page_config(page_title="CryptoPulse", page_icon="◆", layout="wide")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
    }}

    .block-container {{
        padding-top: 2.5rem;
        max-width: 1100px;
    }}

    /* ---- masthead ---- */
    .masthead {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-bottom: 1px solid {BORDER};
        padding-bottom: 14px;
        margin-bottom: 28px;
    }}
    .masthead-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.5rem;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.01em;
    }}
    .masthead-sub {{
        font-size: 0.8rem;
        color: {TEXT_SECONDARY};
        margin-top: 2px;
    }}
    .live-badge {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: {POSITIVE};
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .live-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: {POSITIVE};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.35; }}
        100% {{ opacity: 1; }}
    }}

    /* ---- hero ---- */
    .hero {{
        margin-bottom: 22px;
    }}
    .hero-symbol {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: {TEXT_SECONDARY};
        letter-spacing: 0.04em;
    }}
    .hero-price {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        color: {TEXT_PRIMARY};
        line-height: 1.1;
    }}
    .hero-change {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1rem;
        font-weight: 500;
    }}

    /* ---- stat strip ---- */
    .stat-strip {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        border: 1px solid {BORDER};
        margin-bottom: 24px;
    }}
    .stat-cell {{
        padding: 14px 18px;
        border-right: 1px solid {BORDER};
    }}
    .stat-cell:last-child {{
        border-right: none;
    }}
    .stat-label {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        color: {TEXT_SECONDARY};
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }}
    .stat-value {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.35rem;
        color: {TEXT_PRIMARY};
    }}

    /* ---- anomaly log ---- */
    .log-header {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        color: {TEXT_PRIMARY};
        margin: 8px 0 10px 0;
    }}
    .log-row {{
        display: grid;
        grid-template-columns: 140px 140px 1fr;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        padding: 8px 0;
        border-bottom: 1px solid {BORDER};
        color: {TEXT_PRIMARY};
    }}
    .log-row.header {{
        color: {TEXT_SECONDARY};
        font-size: 0.7rem;
        letter-spacing: 0.05em;
    }}
    .log-z {{
        color: {AMBER};
    }}

    /* ---- native widget tweaks ---- */
    div[data-testid="stSelectbox"] label, div[data-testid="stSlider"] label {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.72rem !important;
        color: {TEXT_SECONDARY} !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

# ---- masthead --------------------------------------------------------

st.markdown(
    f"""
    <div class="masthead">
        <div>
            <div class="masthead-title">◆ CRYPTOPULSE</div>
            <div class="masthead-sub">live ingestion pipeline · automated anomaly detection</div>
        </div>
        <div class="live-badge"><div class="live-dot"></div> LIVE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

coins = list_tracked_coins()

if not coins:
    st.warning(
        "No data yet. Run `python ingest.py` at least once "
        "(or start `python scheduler.py`) to populate the database."
    )
    st.stop()

col_left, col_right = st.columns([1, 1])
with col_left:
    selected_coin = st.selectbox("Coin", options=sorted(coins))
with col_right:
    method = st.radio(
        "Anomaly detection method",
        options=["Rolling z-score", "Isolation Forest"],
        horizontal=True,
    )

lookback_hours = st.slider("Lookback window (hours)", 1, 168, 48)

rows = fetch_history(selected_coin, limit_hours=lookback_hours)

if not rows:
    st.info("No data in this time window yet. Try a longer lookback.")
    st.stop()

df = pd.DataFrame(
    rows,
    columns=[
        "coin_id",
        "price_usd",
        "market_cap_usd",
        "volume_24h_usd",
        "pct_change_24h",
        "fetched_at",
    ],
)
df["fetched_at"] = pd.to_datetime(df["fetched_at"])

if method == "Rolling z-score":
    result = rolling_zscore(df)
else:
    result = isolation_forest_flags(df)

anomalies = result[result["is_anomaly"]]

latest_price = result["price_usd"].iloc[-1]
change_24h = result["pct_change_24h"].iloc[-1]
change_color = POSITIVE if (change_24h or 0) >= 0 else NEGATIVE
change_arrow = "▲" if (change_24h or 0) >= 0 else "▼"
symbol = TICKER_SYMBOLS.get(selected_coin, "◆")

# ---- hero --------------------------------------------------------------

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-symbol">{symbol} {selected_coin.upper()} / USD</div>
        <div class="hero-price">${latest_price:,.2f}</div>
        <div class="hero-change" style="color:{change_color};">
            {change_arrow} {abs(change_24h):.2f}% <span style="color:{TEXT_SECONDARY}; font-weight:400;">24h</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- stat strip ----------------------------------------------------------

window_change = 0.0
if result["price_usd"].iloc[0]:
    window_change = (result["price_usd"].iloc[-1] / result["price_usd"].iloc[0] - 1) * 100
window_color = POSITIVE if window_change >= 0 else NEGATIVE

st.markdown(
    f"""
    <div class="stat-strip">
        <div class="stat-cell">
            <div class="stat-label">DATA POINTS</div>
            <div class="stat-value">{len(result)}</div>
        </div>
        <div class="stat-cell">
            <div class="stat-label">ANOMALIES FLAGGED</div>
            <div class="stat-value" style="color:{AMBER if len(anomalies) else TEXT_PRIMARY};">{len(anomalies)}</div>
        </div>
        <div class="stat-cell">
            <div class="stat-label">WINDOW CHANGE</div>
            <div class="stat-value" style="color:{window_color};">{window_change:+.2f}%</div>
        </div>
        <div class="stat-cell">
            <div class="stat-label">METHOD</div>
            <div class="stat-value" style="font-size:1.05rem;">{method.split(' ')[0].upper()}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- chart -----------------------------------------------------------

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=result["fetched_at"],
        y=result["price_usd"],
        mode="lines",
        name=f"{selected_coin} price (USD)",
        line=dict(width=2, color=AMBER),
        fill="tozeroy",
        fillcolor="rgba(232, 163, 61, 0.06)",
    )
)
if not anomalies.empty:
    fig.add_trace(
        go.Scatter(
            x=anomalies["fetched_at"],
            y=anomalies["price_usd"],
            mode="markers",
            name="Anomaly",
            marker=dict(size=11, symbol="diamond", color=NEGATIVE, line=dict(width=1, color=BG)),
        )
    )
fig.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=20, b=10),
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="IBM Plex Mono, monospace", color=TEXT_SECONDARY, size=11),
    xaxis=dict(showgrid=False, showline=True, linecolor=BORDER, zeroline=False),
    yaxis=dict(
        showgrid=True,
        gridcolor=BORDER,
        showline=False,
        zeroline=False,
        tickprefix="$",
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=TEXT_SECONDARY)),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ---- anomaly log --------------------------------------------------------

st.markdown('<div class="log-header">FLAGGED ANOMALIES</div>', unsafe_allow_html=True)

if not anomalies.empty:
    rows_html = ['<div class="log-row header"><div>TIME</div><div>PRICE</div><div>SEVERITY</div></div>']
    for _, r in anomalies.tail(15).iloc[::-1].iterrows():
        time_str = r["fetched_at"].strftime("%m/%d %H:%M")
        price_str = f"${r['price_usd']:,.2f}"
        z = r.get("z_score")
        severity = f'<span class="log-z">z = {z:.2f}</span>' if pd.notna(z) else '<span class="log-z">flagged</span>'
        rows_html.append(
            f'<div class="log-row"><div>{time_str}</div><div>{price_str}</div><div>{severity}</div></div>'
        )
    st.markdown("".join(rows_html), unsafe_allow_html=True)
else:
    st.markdown(
        f'<div style="color:{TEXT_SECONDARY}; font-family: IBM Plex Mono, monospace; font-size: 0.85rem; padding: 8px 0;">No anomalies in this window.</div>',
        unsafe_allow_html=True,
    )

with st.expander("Raw data"):
    st.dataframe(result, use_container_width=True)