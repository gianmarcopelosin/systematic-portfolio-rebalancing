# Validation against the final Chapter 7 tables

The reconstructed public script was executed against the recovered
`koyfin_2026-08-12-3.csv` attachment. It produced 139 monthly observations and
reproduced the reported thesis results to rounding precision.

## Balanced 60/40

| Rule | CAGR | Annualised volatility | Maximum drawdown | Average drift | Annual turnover | Rebalances |
|---|---:|---:|---:|---:|---:|---:|
| Buy & Hold | 7.95% | 9.93% | -14.05% | 11.44% | 0.00% | 0 |
| Annual | 6.85% | 8.99% | -14.26% | 2.05% | 2.64% | 11 |
| Threshold | 6.92% | 9.11% | -14.19% | 2.63% | 1.89% | 4 |

## Ending equity exposure

| Model portfolio | Target | Buy & Hold | Annual | Threshold |
|---|---:|---:|---:|---:|
| Conservative 20/80 | 20.00% | 43.54% | 21.96% | 22.75% |
| Moderate 40/60 | 40.00% | 67.28% | 42.87% | 45.87% |
| Balanced 60/40 | 60.00% | 82.23% | 62.80% | 66.79% |
| Growth 80/20 | 80.00% | 92.50% | 81.83% | 85.55% |

## Balanced threshold sensitivity

| Threshold | Rebalances | Annual turnover | Average drift | Maximum drift | CAGR |
|---|---:|---:|---:|---:|---:|
| 3 pp | 8 | 2.51% | 1.81% | 5.49% | 6.81% |
| 5 pp | 4 | 1.89% | 2.63% | 6.93% | 6.92% |
| 10 pp | 2 | 1.82% | 4.80% | 11.07% | 7.15% |

## Annual-strategy stress periods

| Model portfolio | February-March 2020 | Full-year 2020 | Full-year 2022 |
|---|---:|---:|---:|
| Conservative 20/80 | -7.25% | 4.03% | -14.81% |
| Moderate 40/60 | -10.00% | 4.49% | -14.54% |
| Balanced 60/40 | -12.78% | 4.95% | -14.26% |
| Growth 80/20 | -15.59% | 5.41% | -13.98% |

## Provenance note

This repository therefore preserves the recovered methodology
in a cleaned command-line script and validates it against the final reported
tables. It does not reintroduce the discarded mean-variance-optimisation design.
