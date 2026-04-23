import streamlit as st
import plotly.express as px

from src.sec_live import fetch_companyfacts, fetch_submissions
from src.baseline_build import build_baseline_from_sec
from src.dcf_mc import Params, simulate, summarize
from src.price_live import get_price
from src.cik_lookup import ticker_to_cik10
from src.implied import implied_wacc, implied_growth

st.set_page_config(page_title="Live SEC Monte Carlo DCF", layout="wide")
st.title("Live SEC‑Based Monte Carlo DCF Valuation (Any Ticker)")

# SEC User-Agent is required for EDGAR access; store in Streamlit Cloud secrets.
SEC_USER_AGENT = st.secrets.get("SEC_USER_AGENT", "Prashant prashjoshi74@gmail.com")

# --- Sidebar: ticker + simulation controls
st.sidebar.header("Company")
ticker = st.sidebar.text_input("Ticker (e.g., AAPL, MSFT, TSLA)", value="AAPL").upper().strip()

st.sidebar.header("Simulation Controls")
years = st.sidebar.slider("Forecast years", 3, 10, 5)
sims = st.sidebar.slider("Simulations", 5_000, 50_000, 20_000, step=5_000)
seed = st.sidebar.number_input("Random seed", value=42)

st.sidebar.subheader("Distributions")
growth_mu = st.sidebar.slider("Growth μ", -0.05, 0.15, 0.05, step=0.005)
growth_sigma = st.sidebar.slider("Growth σ", 0.00, 0.15, 0.03, step=0.005)
wacc_mu = st.sidebar.slider("WACC μ", 0.04, 0.15, 0.08, step=0.005)
wacc_sigma = st.sidebar.slider("WACC σ", 0.00, 0.05, 0.01, step=0.005)
terminal_g = st.sidebar.slider("Terminal growth g", 0.00, 0.05, 0.03, step=0.0025)

refresh = st.sidebar.button("Refresh SEC data")

# --- Resolve ticker -> CIK
cik10 = ticker_to_cik10(ticker, user_agent=SEC_USER_AGENT)

# --- Load SEC data (cached). If ticker not found in SEC map, we skip SEC fundamentals gracefully.
@st.cache_data(ttl=6 * 60 * 60)
def load_sec(cik: str):
    subs = fetch_submissions(cik, SEC_USER_AGENT)
    facts = fetch_companyfacts(cik, SEC_USER_AGENT)
    return subs, facts

if refresh:
    load_sec.clear()

# --- Market price via yfinance (in price_live.py)
price, price_date, price_status = get_price(ticker)

tab1, tab2, tab3 = st.tabs(["Live Data", "Monte Carlo Valuation", "Export"])

# -----------------------------
# TAB 1: Live Data
# -----------------------------
with tab1:
    st.subheader("Live Inputs")

    col1, col2 = st.columns(2)
    with col2:
        st.metric("Market Price", f"${price:,.2f}" if price else "Unavailable")
        st.caption(f"Price date: {price_date} | status: {price_status}")

    if cik10 is None:
        st.warning(
            "SEC fundamentals unavailable for this ticker (CIK not found in SEC mapping). "
            "Price via yfinance may still work."
        )
    else:
        subs, facts = load_sec(cik10)
        baseline = build_baseline_from_sec(facts)

        with col1:
            st.metric("FCF₀ (Operating CF − CapEx)", f"${baseline.fcf0:,.0f}")
            st.metric("Shares Outstanding", f"{baseline.shares_outstanding:,.0f}")

        st.subheader("SEC Fact Source Metadata")
        st.json(baseline.meta)

# -----------------------------
# TAB 2: Monte Carlo Valuation
# -----------------------------
with tab2:
    st.subheader("Monte Carlo DCF Results")

    if cik10 is None:
        st.info(
            "Monte Carlo valuation requires SEC fundamentals (FCF₀ and shares). "
            "Choose a ticker with SEC filings (e.g., AAPL, MSFT, TSLA)."
        )
    else:
        # Load fundamentals
        subs, facts = load_sec(cik10)
        baseline = build_baseline_from_sec(facts)

        params = Params(
            fcf0=baseline.fcf0,
            shares=baseline.shares_outstanding,
            years=years,
            sims=sims,
            seed=seed,
            growth_mu=growth_mu,
            growth_sigma=growth_sigma,
            wacc_mu=wacc_mu,
            wacc_sigma=wacc_sigma,
            terminal_g=terminal_g,
        )

        df = simulate(params)
        summary = summarize(df["value_per_share"])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mean value / share", f"${summary['mean']:,.2f}")
            st.metric("Median value / share", f"${summary['median']:,.2f}")
            st.metric("5–95% range", f"{summary['p05']:,.2f} – {summary['p95']:,.2f}")

        with col2:
            if price:
                prob = (df["value_per_share"] > price).mean()
                st.metric("P(Intrinsic > Market)", f"{prob*100:.1f}%")

        fig = px.histogram(df, x="value_per_share", nbins=60, title="Intrinsic Value Distribution (per share)")
        if price:
            fig.add_vline(x=price, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

        # Save to session state for Export tab
        st.session_state["results"] = df
        st.session_state["summary"] = summary

        # =========================================================
        # Market‑Implied Assumptions (Reverse DCF)  ✅ NEW SECTION
        # =========================================================
        st.subheader("Market‑Implied Assumptions (Reverse DCF)")

        if price is None or price_status == "unavailable":
            st.info("Market price is unavailable, so implied WACC/growth cannot be computed.")
        else:
            fcf0 = float(baseline.fcf0)
            shares = float(baseline.shares_outstanding)

            # Implied WACC: hold growth = growth_mu constant, solve for WACC
            iw = implied_wacc(
                fcf0=fcf0,
                shares=shares,
                years=int(years),
                growth=float(growth_mu),
                terminal_g=float(terminal_g),
                market_price=float(price),
                low=0.02,
                high=0.30,
            )

            # Implied growth: hold WACC = wacc_mu constant, solve for growth
            ig = implied_growth(
                fcf0=fcf0,
                shares=shares,
                years=int(years),
                wacc=float(wacc_mu),
                terminal_g=float(terminal_g),
                market_price=float(price),
                low=-0.20,
                high=0.30,
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("Market price", f"${price:,.2f}")
                st.caption(f"Price date: {price_date} | status: {price_status}")

            with c2:
                if iw is None:
                    st.metric("Implied WACC", "No solution")
                    st.caption(
                        "No WACC in [2%, 30%] makes the DCF equal the market price "
                        "(given your selected growth μ and terminal g)."
                    )
                else:
                    st.metric("Implied WACC", f"{iw*100:.2f}%")
                    st.caption(
                        f"Holding growth μ = {growth_mu*100:.2f}% and terminal g = {terminal_g*100:.2f}%"
                    )

            with c3:
                if ig is None:
                    st.metric("Implied growth", "No solution")
                    st.caption(
                        "No growth in [-20%, 30%] makes the DCF equal the market price "
                        "(given your selected WACC μ and terminal g)."
                    )
                else:
                    st.metric("Implied growth", f"{ig*100:.2f}%")
                    st.caption(
                        f"Holding WACC μ = {wacc_mu*100:.2f}% and terminal g = {terminal_g*100:.2f}%"
                    )

            # Store implied outputs for export if desired
            st.session_state["implied"] = {
                "market_price": float(price),
                "implied_wacc": None if iw is None else float(iw),
                "implied_growth": None if ig is None else float(ig),
                "assumptions_used": {
                    "growth_mu": float(growth_mu),
                    "wacc_mu": float(wacc_mu),
                    "terminal_g": float(terminal_g),
                    "years": int(years),
                },
            }

# -----------------------------
# TAB 3: Export
# -----------------------------
with tab3:
    st.subheader("Download Results")

    if "results" in st.session_state:
        st.download_button(
            "Download simulation results (CSV)",
            st.session_state["results"].to_csv(index=False),
            "mc_results.csv",
            "text/csv",
        )

    if "implied" in st.session_state:
        st.download_button(
            "Download implied assumptions (JSON)",
            data=str(st.session_state["implied"]),
            file_name="implied_assumptions.json",
            mime="application/json",
        )
