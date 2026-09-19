# Systematic Portfolio Rebalancing

A reproducible Python analysis of allocation drift and annual versus
threshold-based rebalancing across four author-defined UCITS ETF model
portfolios.

## Research question

Once an investor has been assigned to a model portfolio, what happens if the
portfolio is left untouched, rebalanced annually, or monitored monthly and
rebalanced only after a material allocation deviation?

The purpose is not to reproduce a proprietary robo-advisor or estimate an
optimal portfolio. The project isolates portfolio monitoring and systematic
rebalancing as transparent components of automated wealth management.

## Design

- Five ETF proxies: EUNL, IQQE, XGLE, EUN5 and IBCI.
- Four author-defined model portfolios with 20%, 40%, 60% and 80% target equity.
- Three rules: buy-and-hold, annual rebalancing and a five-percentage-point
  threshold rule.
- January 2015 through July 2026, producing 139 monthly return observations.
- Baseline rebalancing friction of 10 basis points per unit of one-way turnover,
  with sensitivity at 0 and 25 basis points.
- Metrics include CAGR, annualised volatility, maximum drawdown, historical
  monthly VaR and Expected Shortfall, allocation drift, turnover and the number
  of rebalances.

## Model portfolios

| Model portfolio | EUNL | IQQE | XGLE | EUN5 | IBCI |
|---|---:|---:|---:|---:|---:|
| Conservative 20/80 | 16% | 4% | 40% | 24% | 16% |
| Moderate 40/60 | 32% | 8% | 30% | 18% | 12% |
| Balanced 60/40 | 48% | 12% | 20% | 12% | 8% |
| Growth 80/20 | 64% | 16% | 10% | 6% | 4% |

## Main finding

Rebalancing did not mechanically improve returns in the historical sample. Its
clearest contribution was maintaining consistency with the intended strategic
allocation. The Balanced buy-and-hold portfolio finished with 82.23% equity,
compared with its 60% target. Annual rebalancing reduced average allocation
drift by approximately 82% relative to buy-and-hold.

The five-percentage-point threshold rule required four interventions for the
Balanced portfolio, compared with eleven annual rebalances. This illustrates
that continuous monitoring does not require continuous trading.

## Run the analysis

1. Create a Python environment and install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Place the Koyfin export at `data/raw/koyfin_2026-08-12-3.csv`.

3. Run:

   ```bash
   python "src/Empirical Portfolio Analysis.py"
   ```

The generated tables and figures are written to `outputs/`.

## Interpretation and limitations

The portfolios and rebalancing bands are modelling choices, not investment
recommendations or validated client risk categories. Results are historical and
descriptive, taxes and advisory fees are excluded, transaction costs are
stylised, and no causal or out-of-sample superiority is claimed. EUR trading
currency does not remove the underlying foreign-currency exposures of the
equity funds.

The project should therefore be interpreted as a transparent
portfolio-accounting experiment rather than an executable trading backtest.
