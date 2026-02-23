import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import norm

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Tac Opps Conviction Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #1A1F2E;
    border: 1px solid #2A2F3E;
    border-left: 4px solid #00D4AA;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem;
    color: #8899AA;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #131720;
    border-right: 1px solid #1E2433;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    border-radius: 8px 8px 0 0;
    padding: 10px 20px;
    color: #8899AA;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background-color: #1A1F2E;
    color: #00D4AA;
    border-bottom: 2px solid #00D4AA;
}

/* Expander */
[data-testid="stExpander"] {
    background-color: #1A1F2E;
    border: 1px solid #2A2F3E;
    border-radius: 12px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #0E1117; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }

/* Header badge */
.header-badge {
    display: inline-block;
    background: linear-gradient(135deg, #00D4AA 0%, #1B6EF3 100%);
    color: #0E1117;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-left: 8px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def geometric_growth_rate(f, p, b, s):
    """Expected log-growth per deal at fraction f."""
    q = 1 - p
    if f <= 0:
        return 0.0
    if f * s >= 1.0:
        return -np.inf
    return p * np.log(1 + f * b) + q * np.log(1 - f * s)


def return_stats(p, b, s, f):
    """Variance and std dev of per-deal returns."""
    q = 1 - p
    if f <= 0 or f * s >= 1.0:
        return 0.0, 0.0, 0.0
    log_win = np.log(1 + f * b)
    log_loss = np.log(1 - f * s)
    g = p * log_win + q * log_loss
    var_log = p * log_win**2 + q * log_loss**2 - g**2
    sigma_log = np.sqrt(max(var_log, 0))
    return g, var_log, sigma_log


def deals_to_double(p, b, s, f):
    """Expected deals to 2x capital."""
    g = geometric_growth_rate(f, p, b, s)
    if g <= 0:
        return np.inf
    return np.log(2) / g


def probability_of_profit(p, b, s, f, n_deals):
    """P(profitable after N deals) via CLT."""
    g, _, sigma_log = return_stats(p, b, s, f)
    if sigma_log <= 0:
        return 1.0 if g > 0 else 0.0
    z = (n_deals * g) / (sigma_log * np.sqrt(n_deals))
    return float(norm.cdf(z))


def drawdown_probability(drawdown_pct, kelly_frac_used):
    """P(ever experiencing drawdown_pct) at fractional Kelly."""
    if kelly_frac_used <= 0:
        return 0.0
    x = 1.0 - drawdown_pct
    exp = (2.0 / kelly_frac_used) - 1.0
    return x ** exp


def prob_halve_before_double(kelly_frac_used):
    """P(halving bankroll before doubling it)."""
    if kelly_frac_used <= 0:
        return 0.0
    exp = (2.0 / kelly_frac_used) - 1.0
    return 1.0 / (2 ** exp)


def variance_drag(p, b, s, f):
    """Gap between arithmetic EV and geometric growth."""
    q = 1 - p
    mu_arith = f * (p * b - q * s)
    g = geometric_growth_rate(f, p, b, s)
    return mu_arith - g


def deal_sharpe_ratio(p, b, s):
    """Edge-to-volatility ratio (position-size independent)."""
    q = 1 - p
    ev = p * b - q * s
    sigma = (b + s) * np.sqrt(p * q)
    return ev / sigma if sigma > 0 else 0.0


def breakeven_win_rate(b, s):
    """Minimum p for positive EV."""
    return s / (b + s)


def expected_max_consecutive_losses(n_deals, p):
    """Expected longest losing streak."""
    q = 1 - p
    if q <= 0 or q >= 1:
        return 0
    return np.log(n_deals) / np.log(1 / q)


# ============================================================
# SIDEBAR — DEAL INPUTS
# ============================================================

st.sidebar.markdown("## Deal Parameters")
st.sidebar.caption("Adjust your conviction and deal economics.")

p_win = st.sidebar.slider(
    "Win Probability (%)",
    min_value=5, max_value=95, value=75, step=5,
    help="Your base-case probability that the deal pays off."
) / 100.0
p_loss = 1.0 - p_win

mom_upside = st.sidebar.slider(
    "Upside Multiple (MoM)",
    min_value=1.00, max_value=5.00, value=1.50, step=0.05,
    format="%.2fx",
    help="Expected return multiple if the deal wins."
)

mom_downside = st.sidebar.slider(
    "Downside Recovery (MoM)",
    min_value=0.00, max_value=1.00, value=0.50, step=0.05,
    format="%.2fx",
    help="How much principal you recover if the deal loses."
)

st.sidebar.markdown("---")
st.sidebar.markdown("## Simulation Settings")

n_deals = st.sidebar.slider(
    "Deal Horizon (# of deals)",
    min_value=5, max_value=100, value=20, step=5,
    help="Number of deals to project forward for probability metrics."
)

fund_size = st.sidebar.number_input(
    "Fund Size ($M)",
    min_value=10, max_value=10000, value=500, step=50,
    help="Total fund AUM for dollar sizing."
)

# ============================================================
# CORE CALCULATIONS
# ============================================================

b = mom_upside - 1.0       # Net profit on win
s = 1.0 - mom_downside     # Net loss on loss
s_safe = max(s, 0.001)

edge = (p_win * b) - (p_loss * s)

if edge <= 0:
    full_kelly = 0.0
else:
    full_kelly = (p_win / s_safe) - (p_loss / b)

half_kelly = full_kelly * 0.50
quarter_kelly = full_kelly * 0.25

half_kelly_cap = min(half_kelly, 0.15)
quarter_kelly_cap = min(quarter_kelly, 0.15)
full_kelly_cap = min(full_kelly, 0.15)

p_breakeven = breakeven_win_rate(b, s_safe)
margin_of_safety = p_win - p_breakeven
sharpe = deal_sharpe_ratio(p_win, b, s_safe)

# Growth rates
g_full = geometric_growth_rate(full_kelly_cap, p_win, b, s_safe)
g_half = geometric_growth_rate(half_kelly_cap, p_win, b, s_safe)
g_quarter = geometric_growth_rate(quarter_kelly_cap, p_win, b, s_safe)

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<h1 style='margin-bottom: 0;'>🎯 The Tac Opps Conviction Engine</h1>
<p style='color: #8899AA; font-size: 1.05rem; margin-top: 4px;'>
    Bayesian Kelly sizing for structured equity & hybrid capital
    <span class='header-badge'>Kelly Sizer v2</span>
</p>
""", unsafe_allow_html=True)

st.markdown("")

# ============================================================
# TOP KPI ROW
# ============================================================

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Implied Edge",
    f"{edge:+.3f}",
    delta="Positive" if edge > 0 else "Negative",
    delta_color="normal" if edge > 0 else "inverse",
)
k2.metric(
    "Full Kelly",
    f"{full_kelly * 100:.1f}%",
    help="Theoretical max — too volatile for deployment."
)
k3.metric(
    "½ Kelly Size",
    f"{half_kelly_cap * 100:.1f}%",
    delta=f"${half_kelly_cap * fund_size:.0f}M",
    help="Moderate conviction. Capped at 15%."
)
k4.metric(
    "¼ Kelly Size",
    f"{quarter_kelly_cap * 100:.1f}%",
    delta=f"${quarter_kelly_cap * fund_size:.0f}M",
    help="Conservative conviction. Capped at 15%."
)
k5.metric(
    "Deal Sharpe",
    f"{sharpe:.2f}",
    help="Edge / volatility — above 0.5 is attractive."
)

st.markdown("")

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "Sizing Dashboard",
    "Risk Analytics",
    "Growth & Probability",
    "Sensitivity Engine",
])

# ============================================================
# TAB 1 — SIZING DASHBOARD
# ============================================================

with tab1:
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.markdown("#### Kelly Scenario Comparison")

        scenario_df = pd.DataFrame({
            "Scenario": ["Full Kelly", "½ Kelly", "¼ Kelly"],
            "Raw Size": [f"{full_kelly * 100:.1f}%", f"{half_kelly * 100:.1f}%", f"{quarter_kelly * 100:.1f}%"],
            "After 15% Cap": [f"{full_kelly_cap * 100:.1f}%", f"{half_kelly_cap * 100:.1f}%", f"{quarter_kelly_cap * 100:.1f}%"],
            "Dollar Size ($M)": [f"${full_kelly_cap * fund_size:,.0f}", f"${half_kelly_cap * fund_size:,.0f}", f"${quarter_kelly_cap * fund_size:,.0f}"],
            "Growth Rate (g)": [f"{g_full * 100:.2f}%" if g_full > -np.inf else "N/A",
                                f"{g_half * 100:.2f}%" if g_half > -np.inf else "N/A",
                                f"{g_quarter * 100:.2f}%" if g_quarter > -np.inf else "N/A"],
            "Risk Profile": [
                "Aggressive — max geometric growth",
                "Balanced — practitioner preferred",
                "Conservative — Tac Opps default"
            ],
        })
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    with right_col:
        st.markdown("#### Deal Quality Scorecard")

        with st.container(border=True):
            sc1, sc2 = st.columns(2)
            sc1.metric("Breakeven Win Rate", f"{p_breakeven * 100:.1f}%")
            sc2.metric("Margin of Safety", f"{margin_of_safety * 100:+.1f}pp")

        with st.container(border=True):
            sc3, sc4 = st.columns(2)
            sc3.metric("EV / Dollar Risked", f"{edge / s_safe:.2f}" if s_safe > 0 else "N/A")
            sc4.metric("Win/Loss Ratio", f"{b / s_safe:.2f}x" if s_safe > 0 else "N/A")

    st.markdown("")

    # Sizing gauge chart
    st.markdown("#### Position Size Gauge")
    fig_gauge = go.Figure()

    fig_gauge.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=quarter_kelly_cap * 100,
        number={"suffix": "%", "font": {"size": 40}},
        delta={"reference": 7.5, "suffix": "%", "increasing": {"color": "#00D4AA"}, "decreasing": {"color": "#FF4B4B"}},
        title={"text": "¼ Kelly (Recommended)", "font": {"size": 16, "color": "#8899AA"}},
        gauge={
            "axis": {"range": [0, 20], "tickwidth": 1, "tickcolor": "#2A2F3E"},
            "bar": {"color": "#00D4AA"},
            "bgcolor": "#1A1F2E",
            "borderwidth": 2,
            "bordercolor": "#2A2F3E",
            "steps": [
                {"range": [0, 5], "color": "#0A2A22"},
                {"range": [5, 10], "color": "#1A3A32"},
                {"range": [10, 15], "color": "#2A4A22"},
                {"range": [15, 20], "color": "#3A1A1A"},
            ],
            "threshold": {
                "line": {"color": "#FF4B4B", "width": 3},
                "thickness": 0.8,
                "value": 15
            },
        },
        domain={"x": [0, 0.45], "y": [0, 1]},
    ))

    fig_gauge.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=half_kelly_cap * 100,
        number={"suffix": "%", "font": {"size": 40}},
        delta={"reference": 10, "suffix": "%", "increasing": {"color": "#00D4AA"}, "decreasing": {"color": "#FF4B4B"}},
        title={"text": "½ Kelly (Aggressive)", "font": {"size": 16, "color": "#8899AA"}},
        gauge={
            "axis": {"range": [0, 20], "tickwidth": 1, "tickcolor": "#2A2F3E"},
            "bar": {"color": "#1B6EF3"},
            "bgcolor": "#1A1F2E",
            "borderwidth": 2,
            "bordercolor": "#2A2F3E",
            "steps": [
                {"range": [0, 5], "color": "#0A1A2A"},
                {"range": [5, 10], "color": "#1A2A3A"},
                {"range": [10, 15], "color": "#2A3A4A"},
                {"range": [15, 20], "color": "#3A1A1A"},
            ],
            "threshold": {
                "line": {"color": "#FF4B4B", "width": 3},
                "thickness": 0.8,
                "value": 15
            },
        },
        domain={"x": [0.55, 1], "y": [0, 1]},
    ))

    fig_gauge.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="#0E1117",
        font={"color": "#FAFAFA"},
    )
    st.plotly_chart(fig_gauge, use_container_width=True)


# ============================================================
# TAB 2 — RISK ANALYTICS
# ============================================================

with tab2:
    r_left, r_right = st.columns(2)

    with r_left:
        st.markdown("#### Drawdown Risk")

        dd_data = []
        for dd_pct in [0.10, 0.20, 0.30, 0.50]:
            dd_data.append({
                "Drawdown": f"{dd_pct * 100:.0f}%",
                "Full Kelly": f"{drawdown_probability(dd_pct, 1.0) * 100:.1f}%",
                "½ Kelly": f"{drawdown_probability(dd_pct, 0.5) * 100:.2f}%",
                "¼ Kelly": f"{drawdown_probability(dd_pct, 0.25) * 100:.3f}%",
            })
        dd_df = pd.DataFrame(dd_data)
        st.dataframe(dd_df, use_container_width=True, hide_index=True)

        st.caption("Probability of **ever** experiencing each drawdown level over infinite horizon.")

    with r_right:
        st.markdown("#### Ruin & Survival")

        surv_data = {
            "Metric": [
                "P(Halve Before Double)",
                "Variance Drag (per deal)",
                f"Max Losing Streak ({n_deals} deals)",
                f"Drawdown from Max Streak",
            ],
        }

        for label, frac, f_val in [("Full Kelly", 1.0, full_kelly_cap),
                                    ("½ Kelly", 0.5, half_kelly_cap),
                                    ("¼ Kelly", 0.25, quarter_kelly_cap)]:
            streak = expected_max_consecutive_losses(n_deals, p_win)
            streak_dd = 1 - (1 - f_val * s_safe) ** streak if f_val * s_safe < 1 else 1.0
            surv_data[label] = [
                f"{prob_halve_before_double(frac) * 100:.2f}%",
                f"{variance_drag(p_win, b, s_safe, f_val) * 100:.3f}%",
                f"{streak:.1f} deals",
                f"{streak_dd * 100:.1f}%",
            ]

        surv_df = pd.DataFrame(surv_data)
        st.dataframe(surv_df, use_container_width=True, hide_index=True)

    st.markdown("")

    # Drawdown probability visualization
    st.markdown("#### Drawdown Probability Curves")

    dd_range = np.linspace(0.01, 0.80, 80)
    fig_dd = go.Figure()

    for label, frac, color in [("Full Kelly", 1.0, "#FF4B4B"),
                                ("½ Kelly", 0.5, "#F97316"),
                                ("¼ Kelly", 0.25, "#00D4AA")]:
        probs = [drawdown_probability(d, frac) * 100 for d in dd_range]
        fig_dd.add_trace(go.Scatter(
            x=dd_range * 100, y=probs,
            mode='lines', name=label,
            line=dict(color=color, width=2.5),
        ))

    fig_dd.update_layout(
        xaxis_title="Drawdown Level (%)",
        yaxis_title="Probability of Ever Occurring (%)",
        height=380,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font={"color": "#FAFAFA"},
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#1A1F2E", zeroline=False),
        yaxis=dict(gridcolor="#1A1F2E", zeroline=False),
    )
    st.plotly_chart(fig_dd, use_container_width=True)


# ============================================================
# TAB 3 — GROWTH & PROBABILITY
# ============================================================

with tab3:
    g_left, g_right = st.columns(2)

    with g_left:
        st.markdown("#### Geometric Growth Rate Curve")
        st.caption("The Kelly fraction maximizes this curve. Overbetting destroys growth.")

        f_range = np.linspace(0.001, min(0.99 / s_safe, 1.0), 200)
        g_vals = [geometric_growth_rate(f, p_win, b, s_safe) * 100 for f in f_range]

        fig_growth = go.Figure()
        fig_growth.add_trace(go.Scatter(
            x=f_range * 100, y=g_vals,
            mode='lines', name="Growth Rate",
            line=dict(color="#1B6EF3", width=2.5),
            fill='tozeroy', fillcolor='rgba(27,110,243,0.1)',
        ))

        # Mark Kelly fractions
        for label, f_val, color in [("Full Kelly", full_kelly_cap, "#FF4B4B"),
                                     ("½ Kelly", half_kelly_cap, "#F97316"),
                                     ("¼ Kelly", quarter_kelly_cap, "#00D4AA")]:
            g_val = geometric_growth_rate(f_val, p_win, b, s_safe) * 100
            fig_growth.add_trace(go.Scatter(
                x=[f_val * 100], y=[g_val],
                mode='markers+text', name=label,
                marker=dict(size=12, color=color, symbol='diamond'),
                text=[label], textposition="top center",
                textfont=dict(color=color, size=11),
            ))

        fig_growth.update_layout(
            xaxis_title="Position Size (% of Fund)",
            yaxis_title="Growth Rate per Deal (%)",
            height=400,
            margin=dict(l=40, r=20, t=20, b=40),
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            font={"color": "#FAFAFA"},
            showlegend=False,
            xaxis=dict(gridcolor="#1A1F2E", zeroline=False),
            yaxis=dict(gridcolor="#1A1F2E", zeroline=False),
        )
        st.plotly_chart(fig_growth, use_container_width=True)

    with g_right:
        st.markdown("#### Probability of Profit Over Time")
        st.caption(f"Confidence of being net profitable after N deals.")

        deal_range = np.arange(1, n_deals + 1)
        fig_prob = go.Figure()

        for label, f_val, color in [("½ Kelly", half_kelly_cap, "#F97316"),
                                     ("¼ Kelly", quarter_kelly_cap, "#00D4AA")]:
            probs = [probability_of_profit(p_win, b, s_safe, f_val, n) * 100 for n in deal_range]
            fig_prob.add_trace(go.Scatter(
                x=deal_range, y=probs,
                mode='lines', name=label,
                line=dict(color=color, width=2.5),
            ))

        fig_prob.add_hline(y=95, line_dash="dot", line_color="#8899AA",
                           annotation_text="95% confidence", annotation_position="bottom right")

        fig_prob.update_layout(
            xaxis_title="Number of Deals",
            yaxis_title="P(Profitable) %",
            yaxis_range=[0, 105],
            height=400,
            margin=dict(l=40, r=20, t=20, b=40),
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            font={"color": "#FAFAFA"},
            legend=dict(x=0.02, y=0.15, bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#1A1F2E", zeroline=False),
            yaxis=dict(gridcolor="#1A1F2E", zeroline=False),
        )
        st.plotly_chart(fig_prob, use_container_width=True)

    # Bottom row — Deals to Double and summary
    st.markdown("")
    d1, d2, d3, d4 = st.columns(4)

    dtd_half = deals_to_double(p_win, b, s_safe, half_kelly_cap)
    dtd_quarter = deals_to_double(p_win, b, s_safe, quarter_kelly_cap)

    d1.metric(
        "Deals to 2x (½ Kelly)",
        f"{dtd_half:.0f}" if dtd_half < np.inf else "N/A",
        help="Expected deals to double fund at ½ Kelly sizing."
    )
    d2.metric(
        "Deals to 2x (¼ Kelly)",
        f"{dtd_quarter:.0f}" if dtd_quarter < np.inf else "N/A",
        help="Expected deals to double fund at ¼ Kelly sizing."
    )
    d3.metric(
        f"P(Profit) after {n_deals} deals (½K)",
        f"{probability_of_profit(p_win, b, s_safe, half_kelly_cap, n_deals) * 100:.1f}%"
    )
    d4.metric(
        f"P(Profit) after {n_deals} deals (¼K)",
        f"{probability_of_profit(p_win, b, s_safe, quarter_kelly_cap, n_deals) * 100:.1f}%"
    )


# ============================================================
# TAB 4 — SENSITIVITY ENGINE
# ============================================================

with tab4:
    st.markdown("#### Sizing Sensitivity: ½ vs ¼ Kelly across Downside Recovery")

    recoveries = np.arange(0.0, 1.05, 0.05)
    sizes_half = []
    sizes_quarter = []

    for rec in recoveries:
        loss_sc = max(1.0 - rec, 0.001)
        e = (p_win * b) - (p_loss * loss_sc)
        if e <= 0:
            k = 0
        else:
            k = max((p_win / loss_sc) - (p_loss / b), 0)
        sizes_half.append(min(k * 0.50, 0.15) * 100)
        sizes_quarter.append(min(k * 0.25, 0.15) * 100)

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x=recoveries, y=sizes_half,
        mode='lines+markers', name="½ Kelly",
        line=dict(color="#F97316", width=2.5),
        marker=dict(size=6, symbol='square'),
    ))
    fig_sens.add_trace(go.Scatter(
        x=recoveries, y=sizes_quarter,
        mode='lines+markers', name="¼ Kelly",
        line=dict(color="#00D4AA", width=2.5),
        marker=dict(size=6),
    ))
    fig_sens.add_trace(go.Scatter(
        x=recoveries, y=sizes_half,
        fill='tonexty', fillcolor='rgba(150,150,150,0.1)',
        line=dict(width=0), showlegend=False, hoverinfo='skip',
    ))
    fig_sens.add_hline(y=15, line_dash="dash", line_color="#FF4B4B",
                       annotation_text="15% Hard Cap", annotation_position="top right")

    fig_sens.update_layout(
        xaxis_title="Downside Recovery (MoM)",
        yaxis_title="Recommended Size (%)",
        title=dict(
            text=f"Assuming {mom_upside:.2f}x Upside & {p_win*100:.0f}% Win Rate",
            font=dict(size=14, color="#8899AA"),
        ),
        height=420,
        margin=dict(l=40, r=20, t=60, b=40),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font={"color": "#FAFAFA"},
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#1A1F2E", zeroline=False, dtick=0.1),
        yaxis=dict(gridcolor="#1A1F2E", zeroline=False),
    )
    st.plotly_chart(fig_sens, use_container_width=True)

    # Win rate sensitivity heatmap
    st.markdown("#### Heatmap: ¼ Kelly Size across Win Rate & Upside Multiple")

    win_rates = np.arange(0.50, 0.96, 0.05)
    upsides = np.arange(1.10, 5.05, 0.20)
    heatmap_data = np.zeros((len(win_rates), len(upsides)))

    for i, wr in enumerate(win_rates):
        for j, up in enumerate(upsides):
            b_h = up - 1.0
            e_h = wr * b_h - (1 - wr) * s_safe
            if e_h <= 0:
                heatmap_data[i, j] = 0
            else:
                k_h = max((wr / s_safe) - ((1 - wr) / b_h), 0)
                heatmap_data[i, j] = min(k_h * 0.25, 0.15) * 100

    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=[f"{u:.1f}x" for u in upsides],
        y=[f"{w*100:.0f}%" for w in win_rates],
        colorscale=[
            [0, "#0E1117"],
            [0.3, "#0A2A22"],
            [0.6, "#00D4AA"],
            [0.8, "#1B6EF3"],
            [1.0, "#8B5CF6"],
        ],
        colorbar=dict(title="Size %", ticksuffix="%"),
        text=np.round(heatmap_data, 1),
        texttemplate="%{text}%",
        textfont={"size": 9},
        hovertemplate="Win Rate: %{y}<br>Upside: %{x}<br>¼ Kelly: %{z:.1f}%<extra></extra>",
    ))

    fig_heat.update_layout(
        xaxis_title="Upside Multiple (MoM)",
        yaxis_title="Win Probability",
        title=dict(
            text=f"¼ Kelly Size (%) — Downside Recovery fixed at {mom_downside:.2f}x",
            font=dict(size=14, color="#8899AA"),
        ),
        height=450,
        margin=dict(l=60, r=20, t=60, b=40),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font={"color": "#FAFAFA"},
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #556677; font-size: 0.8rem; padding: 10px 0;'>
    Tac Opps Conviction Engine v2 &nbsp;|&nbsp; Built on Kelly Criterion with Jas Khaira Guardrails &nbsp;|&nbsp; 15% hard cap
</div>
""", unsafe_allow_html=True)
