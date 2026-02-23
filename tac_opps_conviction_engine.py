import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Tac Opps Conviction Engine", layout="wide")

st.title("🎯 The Tac Opps Conviction Engine (Kelly Sizer)")
st.markdown("A Bayesian sizing tool adjusting the Kelly Criterion for structured equity and hybrid capital.")

# --- SIDEBAR: The Sliders ---
st.sidebar.header("Deal Assumptions")

p_win = st.sidebar.slider("Probability of Win (Base Case) %", min_value=0, max_value=100, value=75, step=5) / 100.0
p_loss = 1.0 - p_win

mom_upside = st.sidebar.slider("Upside Multiple (MoM)", min_value=1.1, max_value=10.0, value=1.5, step=0.1)
mom_downside = st.sidebar.slider("Downside Recovery (MoM)", min_value=0.0, max_value=1.0, value=0.5, step=0.1)

# Convert MoM to Kelly inputs
b = mom_upside - 1.0       # Net Profit
s = 1.0 - mom_downside     # Net Loss (Principal at risk)

# --- CALCULATIONS ---
# Edge = (Probability of Win * Profit) - (Probability of Loss * Loss Amount)
edge = (p_win * b) - (p_loss * s)

if edge <= 0:
    full_kelly = 0.0
else:
    # Full Kelly Formula: f* = (p/s) - (q/b)
    s_safe = max(s, 0.001)
    full_kelly = (p_win / s_safe) - (p_loss / b)

# Kelly scenarios
half_kelly = full_kelly * 0.50
quarter_kelly = full_kelly * 0.25
half_kelly_cap = min(half_kelly, 0.15)
quarter_kelly_cap = min(quarter_kelly, 0.15)

# --- DASHBOARD UI ---
col1, col2, col3, col4 = st.columns(4)

col1.metric("Implied Edge", f"{edge:,.2f}", delta="Positive" if edge > 0 else "Negative", delta_color="normal")
col2.metric("Full Kelly", f"{full_kelly * 100:,.1f}%", help="Theoretical optimal — too aggressive for real deployment.")
col3.metric("½ Kelly Size", f"{half_kelly_cap * 100:,.1f}%", help="Moderate conviction. Capped at 15%.")
col4.metric("¼ Kelly Size", f"{quarter_kelly_cap * 100:,.1f}%", help="Conservative conviction. Capped at 15%.")

st.divider()

# --- COMPARISON TABLE ---
st.subheader("Kelly Scenario Comparison")

scenario_df = pd.DataFrame({
    "Scenario": ["Full Kelly", "½ Kelly", "¼ Kelly"],
    "Raw Size (%)": [f"{full_kelly * 100:,.1f}", f"{half_kelly * 100:,.1f}", f"{quarter_kelly * 100:,.1f}"],
    "After 15% Cap (%)": [f"{min(full_kelly, 0.15) * 100:,.1f}", f"{half_kelly_cap * 100:,.1f}", f"{quarter_kelly_cap * 100:,.1f}"],
    "Risk Profile": ["Aggressive — max geometric growth", "Balanced — preferred by most practitioners", "Conservative — Tac Opps default"],
})
st.table(scenario_df)

st.divider()

# --- VISUALIZATION ---
st.subheader("Sizing Sensitivity Matrix")
st.write("How ½ Kelly and ¼ Kelly sizing change as downside recovery varies:")

recoveries = np.arange(0.0, 1.1, 0.1)
sizes_half = []
sizes_quarter = []

for rec in recoveries:
    loss_scenario = max(1.0 - rec, 0.001)
    e = (p_win * b) - (p_loss * loss_scenario)
    if e <= 0:
        k = 0
    else:
        k = max((p_win / loss_scenario) - (p_loss / b), 0)

    sizes_half.append(min(k * 0.50, 0.15) * 100)
    sizes_quarter.append(min(k * 0.25, 0.15) * 100)

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(recoveries, sizes_half, marker='s', color='#ff7f0e', linewidth=2, label="½ Kelly")
ax.plot(recoveries, sizes_quarter, marker='o', color='#1f77b4', linewidth=2, label="¼ Kelly")
ax.axhline(15, color='red', linestyle='--', linewidth=1, label="Tac Opps 15% Cap")
ax.fill_between(recoveries, sizes_quarter, sizes_half, alpha=0.15, color='grey', label="Sizing range (¼ to ½)")
ax.set_xlabel("Downside Recovery (MoM)")
ax.set_ylabel("Recommended Sizing (%)")
ax.set_title(f"½ vs ¼ Kelly Sizing (Assuming {mom_upside}x Upside & {p_win*100:.0f}% Win Rate)")
ax.grid(True, alpha=0.3)
ax.legend()

st.pyplot(fig)
