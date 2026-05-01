# Live SEC Monte Carlo DCF Valuation

An interactive Streamlit app that pulls real financial data from the SEC EDGAR API and runs a **Monte Carlo Discounted Cash Flow (DCF)** simulation to estimate the intrinsic value of any publicly traded US company — including a reverse-DCF "market-implied assumptions" view.

> **Built with GitHub Copilot** as a practical finance and data-analysis classroom project. See [Using Copilot in Non-CS Courses](#using-copilot-in-a-finance-course) below.

---

## What It Does

| Feature | Description |
|---|---|
| **Live SEC data** | Fetches operating cash flow, CapEx, and shares outstanding directly from SEC EDGAR using the company's CIK number |
| **Monte Carlo simulation** | Runs thousands of DCF scenarios by sampling growth rate and WACC from normal distributions |
| **Intrinsic value distribution** | Shows a histogram of per-share values with a market-price benchmark line |
| **Reverse DCF (implied assumptions)** | Solves for the WACC or growth rate that makes the DCF equal the current market price |
| **Export** | Download simulation results as CSV and implied assumptions as JSON |

---

## Getting Started

### Prerequisites

- Python 3.10+
- A GitHub account with [GitHub Copilot](https://github.com/copilot) enabled (optional but recommended for learning)

### Installation

```bash
git clone https://github.com/prajo31/aapl-sec-mc-valuation.git
cd aapl-sec-mc-valuation
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Streamlit Cloud

Set the `SEC_USER_AGENT` secret (format: `"Your Name email@example.com"`) in your Streamlit Cloud app settings — this is required by the SEC EDGAR API's fair-use policy.

---

## Key Concepts

### Discounted Cash Flow (DCF)

The intrinsic value of a company is estimated by discounting its future free cash flows (FCF) back to today:

```
FCF_t  = FCF₀ × (1 + growth)^t         # projected free cash flow in year t
PV     = Σ FCF_t / (1 + WACC)^t        # present value of FCFs
TV     = FCF_N × (1 + g) / (WACC − g)  # Gordon Growth terminal value
EV     = PV(FCFs) + PV(TV)             # enterprise value
Value/share = EV / shares_outstanding
```

### Monte Carlo Simulation

Rather than using single point-estimates for growth and WACC, the app draws thousands of random samples from user-specified normal distributions, producing a *distribution* of intrinsic values. This reflects real-world uncertainty in financial forecasting.

### Reverse DCF (Implied Assumptions)

Given the current market price, we can ask: *"What growth rate / WACC would the market need to believe to justify this price?"* The app solves for these values using bisection, revealing the assumptions already embedded in the stock price.

---

## Using Copilot in a Finance Course

This project is designed as a hands-on learning resource for **economics and finance students**, aligned with the [GitHub Education guide on using Copilot in non-CS courses](https://github.com/github-education-resources/teacher-toolbox/blob/main/ai-education/copilot-non-cs-courses.md).

### Learning Objectives

- Understand how DCF valuation models work and what drives intrinsic value
- Interpret probability distributions and ranges rather than single-point forecasts
- Read real SEC EDGAR filings and understand the data behind financial models
- Use GitHub Copilot as a thinking partner to explore, modify, and extend financial code

### Sample Prompts for Students

Use [github.com/copilot](https://github.com/copilot) or Copilot in VS Code to explore and extend this project:

**Understanding the model:**
> "Explain the Gordon Growth Model used in `src/dcf_mc.py`. What happens to intrinsic value when WACC approaches the terminal growth rate, and why?"

**Sensitivity analysis:**
> "I'm looking at the DCF model in `src/dcf_mc.py`. How would I modify `simulate()` to also vary the terminal growth rate `g` randomly, instead of keeping it fixed? What distribution would make sense?"

**Interpreting results:**
> "The Monte Carlo simulation shows a mean intrinsic value of $180 and a market price of $220. The P(Intrinsic > Market) is 23%. What does this mean for an investor, and what assumptions could change this conclusion?"

**Extending the model:**
> "The current model uses a single-stage growth rate. How would I extend `src/dcf_mc.py` to use two growth stages — a high-growth phase for years 1–5 and a slower phase for years 6–10 — before applying the terminal value?"

**Data exploration:**
> "Look at `src/sec_live.py` and `src/baseline_build.py`. What SEC EDGAR API endpoints are being called, and how does the app handle companies that use different GAAP tags for operating cash flow?"

### Classroom Activities

1. **Sensitivity analysis exercise** — Adjust the growth μ/σ and WACC μ/σ sliders. How does the shape of the value distribution change? What does a wider distribution tell you about forecast uncertainty?

2. **Reverse DCF discussion** — Run the app for a high-P/E stock. What implied growth rate does the market price require? Is that realistic? Compare with analyst consensus forecasts.

3. **Cross-company comparison** — Compare the intrinsic value distributions of two companies in the same sector. What explains the differences in FCF₀, growth assumptions, or risk (WACC)?

4. **Prompt reflection log** — After using Copilot to extend or debug the model, write a short reflection: What did Copilot get right? What did it miss? What follow-up questions did it prompt you to ask?

---

## Project Structure

```
app.py                  # Streamlit UI
requirements.txt
src/
  sec_live.py           # SEC EDGAR API client (company facts, submissions)
  cik_lookup.py         # Ticker → CIK mapping via SEC company_tickers.json
  baseline_build.py     # Extract FCF₀ and shares from EDGAR facts
  dcf_mc.py             # Monte Carlo DCF engine (Params, simulate, summarize)
  implied.py            # Reverse DCF: implied WACC and implied growth solvers
  price_live.py         # Live market price via yfinance
```

---

## Responsible AI Use

When using Copilot to work with this project:

- **Verify financial formulas** — always cross-check DCF outputs against textbook definitions
- **Check data sources** — confirm that SEC tags used in `baseline_build.py` are correct for your target company
- **Disclose AI assistance** — if submitting this work for a course, follow your institution's AI use policy and add an AI use statement explaining how Copilot was used

---

## License

MIT
