import streamlit as st
import plotly.express as px

from src.sec_live import fetch_companyfacts, fetch_submissions, DEFAULT_CIK10
from src.baseline_build import build_baseline_from_sec
from src.dcf_mc import Params, simulate, summarize
from src.price_live import get_price
from src.cik_lookup import ticker_to_cik10
from src.implied import implied_wacc, implied_growth

st.set_page_config(page_title="Live SEC Monte Carlo DCF", layout="wide")
st.title("Live SEC‑Based Monte Carlo DCF Valuation (Any Ticker)")

# SEC User-Agent is required for EDGAR access; store in Streamlit Cloud secrets. [7](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)[1](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
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

price, price_date, price_status = get_price(ticker)

tab1, tab2, tab3 = st.tabs(["Live Data", "Monte Carlo Valuation", "Export"])

with tab1:
    st.subheader("Live Inputs")

    col1, col2 = st.columns(2)
    with col2:
        st.metric("Market Price", f"${price:,.2f}" if price else "Unavailable")
        st.caption(f"Price date: {price_date} | status: {price_status}")

    if cik10 is None:
        st.warning("SEC fundamentals unavailable for this ticker (CIK not found in SEC mapping). Price via yfinance may still work.")
    else:
        subs, facts = load_sec(cik10)
        baseline = build_baseline_from_sec(facts)

        with col1:
            st.metric("FCF₀ (Operating CF − CapEx)", f"${baseline.fcf0:,.0f}")
            st.metric("Shares Outstanding", f"{baseline.shares_outstanding:,.0f}")

        st.subheader("SEC Fact Source Metadata")
        st.json(baseline.meta)

with tab2:
    st.subheader("Monte Carlo DCF Results")

    if cik10 is None:
        st.info("Monte Carlo valuation requires SEC fundamentals (FCF₀ and shares). Choose a ticker with SEC filings (e.g., AAPL, MSFT, TSLA).")
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
            st.metric("5–95% range", f"${summary['p05']:,.2f} – ${summary['p95']:,.2f}")

        with col2:
            if price:
                prob = (df["value_per_share"] > price).mean()
                st.metric("P(Intrinsic > Market)", f"{prob*100:.1f}%")

        fig = px.histogram(df, x="value_per_share", nbins=60, title="Intrinsic Value Distribution (per share)")
        if price:
            fig.add_vline(x=price, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

        st.session_state["results"] = df
        st.session_state["summary"] = summary

with tab3:
    st.subheader("Download Results")

    if "results" in st.session_state:
        st.download_button(
            "Download simulation results (CSV)",
            st.session_state["results"].to_csv(index=False),
            "mc_results.csv",
            "text/csv",
        )
