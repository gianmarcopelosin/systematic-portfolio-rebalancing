#!/usr/bin/env python3
"""Empirical Analysis on model-portfolio and rebalancing.

It uses Koyfin's fields labelled "Adj. Close", converts the daily
observations to month-end prices, and evaluates four author-defined model
portfolios under buy-and-hold, annual, and threshold-based rebalancing.

This is a historical, descriptive portfolio-accounting simulation. It is not
investment advice and is not an executable trading strategy.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
from collections import OrderedDict, defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


TICKERS = ["EUNL", "IQQE", "XGLE", "EUN5", "IBCI"]

ASSET_NAMES = {
    "EUNL": "Developed-world equities",
    "IQQE": "Emerging-market equities",
    "XGLE": "Eurozone government bonds",
    "EUN5": "Euro investment-grade corporate bonds",
    "IBCI": "Euro inflation-linked government bonds",
}

MODEL_PORTFOLIOS = OrderedDict(
    {
        "Conservative 20/80": np.array([0.16, 0.04, 0.40, 0.24, 0.16]),
        "Moderate 40/60": np.array([0.32, 0.08, 0.30, 0.18, 0.12]),
        "Balanced 60/40": np.array([0.48, 0.12, 0.20, 0.12, 0.08]),
        "Growth 80/20": np.array([0.64, 0.16, 0.10, 0.06, 0.04]),
    }
)

RULES = ["Buy & Hold", "Annual", "Threshold"]
BASE_THRESHOLD = 0.05
BASE_COST_BPS = 10
COST_SCENARIOS = [0, 10, 25]
THRESHOLD_SCENARIOS = [0.03, 0.05, 0.10]
BACKTEST_START = (2015, 1)
FINAL_COMPLETE_MONTH = (2026, 7)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/koyfin_2026-08-12-3.csv"),
        help="Koyfin CSV containing the five 'Adj. Close' columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs"),
        help="Directory in which CSV tables and PNG figures are written.",
    )
    return parser.parse_args()


def write_csv(output_dir: Path, filename: str, headers: list[str], rows: list[list]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / filename).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def max_drawdown(returns: np.ndarray) -> tuple[float, np.ndarray]:
    wealth = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(wealth)
    drawdown = wealth / peak - 1
    return float(drawdown.min()), drawdown


def performance_metrics(
    returns: np.ndarray,
    turnovers: np.ndarray | None = None,
    rebalance_flags: np.ndarray | None = None,
    target: np.ndarray | None = None,
    pre_weights: np.ndarray | None = None,
) -> tuple[dict[str, float], np.ndarray]:
    observations = len(returns)
    years = observations / 12.0
    final_wealth = float(np.prod(1 + returns))
    standard_deviation = float(np.std(returns, ddof=1))
    cagr = final_wealth ** (1 / years) - 1
    annual_mean = float(np.mean(returns) * 12)
    annual_volatility = standard_deviation * math.sqrt(12)
    sharpe_rf0 = float(np.mean(returns) / standard_deviation * math.sqrt(12))

    downside_returns = np.minimum(returns, 0)
    downside_deviation = math.sqrt(float(np.mean(downside_returns**2))) * math.sqrt(12)
    sortino_rf0 = annual_mean / downside_deviation if downside_deviation > 0 else np.nan

    maximum_drawdown, drawdowns = max_drawdown(returns)
    fifth_percentile = float(np.quantile(returns, 0.05))
    tail_returns = returns[returns <= fifth_percentile]

    results: dict[str, float] = {
        "CAGR": cagr,
        "Annualised mean return": annual_mean,
        "Annualised volatility": annual_volatility,
        "Sharpe rf0": sharpe_rf0,
        "Sortino rf0": float(sortino_rf0),
        "Maximum drawdown": maximum_drawdown,
        "Monthly VaR 95%": -fifth_percentile,
        "Monthly CVaR 95%": -float(tail_returns.mean()),
        "Positive months": float(np.mean(returns > 0)),
        "Final wealth": final_wealth,
    }

    if turnovers is not None:
        results["Total turnover"] = float(turnovers.sum())
        results["Average annual turnover"] = float(turnovers.sum() / years)

    if rebalance_flags is not None:
        results["Number of rebalances"] = int(rebalance_flags.sum())

    if target is not None and pre_weights is not None:
        drift = 0.5 * np.sum(np.abs(pre_weights - target), axis=1)
        target_equity = float(target[0] + target[1])
        actual_equity = pre_weights[:, 0] + pre_weights[:, 1]
        results["Average allocation drift"] = float(drift.mean())
        results["Maximum allocation drift"] = float(drift.max())
        results["Average equity abs deviation"] = float(
            np.mean(np.abs(actual_equity - target_equity))
        )
        results["Maximum equity abs deviation"] = float(
            np.max(np.abs(actual_equity - target_equity))
        )

    return results, drawdowns


def simulate(
    returns: np.ndarray,
    months: list[tuple[int, int]],
    target: np.ndarray,
    rule: str,
    threshold: float = BASE_THRESHOLD,
    cost_bps: float = 0,
) -> dict[str, np.ndarray]:
    holdings = target.astype(float).copy()
    previous_value = 1.0

    values: list[float] = []
    portfolio_returns: list[float] = []
    pre_weights: list[np.ndarray] = []
    post_weights: list[np.ndarray] = []
    turnovers: list[float] = []
    costs: list[float] = []
    flags: list[bool] = []

    for asset_returns, year_month in zip(returns, months):
        holdings *= 1 + asset_returns
        gross_value = float(holdings.sum())
        weights_before_trade = holdings / gross_value

        if rule == "Buy & Hold":
            rebalance = False
        elif rule == "Annual":
            rebalance = year_month[1] == 12
        elif rule == "Threshold":
            rebalance = float(np.max(np.abs(weights_before_trade - target))) > threshold
        else:
            raise ValueError(f"Unknown rule: {rule}")

        turnover = 0.0
        cost = 0.0
        if rebalance:
            turnover = 0.5 * float(np.sum(np.abs(target - weights_before_trade)))
            cost = cost_bps / 10000.0 * turnover * gross_value
            net_value = gross_value - cost
            holdings = target * net_value
        else:
            net_value = gross_value

        portfolio_return = net_value / previous_value - 1
        previous_value = net_value

        values.append(net_value)
        portfolio_returns.append(portfolio_return)
        pre_weights.append(weights_before_trade.copy())
        post_weights.append(holdings / net_value)
        turnovers.append(turnover)
        costs.append(cost)
        flags.append(rebalance)

    return {
        "values": np.asarray(values),
        "returns": np.asarray(portfolio_returns),
        "pre_weights": np.asarray(pre_weights),
        "post_weights": np.asarray(post_weights),
        "turnovers": np.asarray(turnovers),
        "costs": np.asarray(costs),
        "rebalanced": np.asarray(flags, dtype=bool),
    }


def load_monthly_returns(input_csv: Path) -> tuple[list[tuple[int, int]], np.ndarray, np.ndarray]:
    with input_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    month_end: defaultdict[tuple[int, int], dict[str, tuple[dt.date, float]]] = defaultdict(dict)
    for row in rows:
        date = dt.datetime.strptime(row["Date"], "%m-%d-%Y").date()
        year_month = (date.year, date.month)
        for ticker in TICKERS:
            raw_value = row[f"{ticker} Adj. Close"].strip()
            if raw_value:
                month_end[year_month][ticker] = (date, float(raw_value))

    common_months = [
        year_month
        for year_month in sorted(month_end)
        if year_month <= FINAL_COMPLETE_MONTH
        and all(ticker in month_end[year_month] for ticker in TICKERS)
    ]
    if len(common_months) < 2:
        raise ValueError("The input does not contain at least two common month-end observations.")

    prices = np.asarray(
        [
            [month_end[year_month][ticker][1] for ticker in TICKERS]
            for year_month in common_months
        ],
        dtype=float,
    )
    returns_all = prices[1:] / prices[:-1] - 1
    return_months_all = common_months[1:]
    mask = np.asarray([month >= BACKTEST_START for month in return_months_all])
    months = [month for month in return_months_all if month >= BACKTEST_START]
    return months, returns_all[mask], prices


def period_return(returns: np.ndarray, months: list[tuple[int, int]], selected: set[tuple[int, int]]) -> float:
    observations = np.asarray([value for value, month in zip(returns, months) if month in selected])
    return float(np.prod(1 + observations) - 1)


def make_figures(
    output_dir: Path,
    months: list[tuple[int, int]],
    asset_returns: np.ndarray,
    simulations: dict[tuple[str, str], dict[str, np.ndarray]],
    performance: dict[tuple[str, str], dict[str, float]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    dates = [dt.date(year, month, 1) for year, month in months]

    corr = np.corrcoef(asset_returns, rowvar=False)
    fig, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    axis.set_xticks(range(len(TICKERS)), TICKERS)
    axis.set_yticks(range(len(TICKERS)), TICKERS)
    for i in range(len(TICKERS)):
        for j in range(len(TICKERS)):
            axis.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=9)
    axis.set_title("Correlation matrix of monthly ETF returns")
    fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_7_1_correlation_matrix.png", dpi=300)
    plt.close(fig)

    wealth = np.cumprod(1 + asset_returns, axis=0)
    fig, axis = plt.subplots(figsize=(10, 6))
    for index, ticker in enumerate(TICKERS):
        axis.plot(dates, wealth[:, index], label=ticker, linewidth=1.8)
    axis.set_title("Growth of EUR 1 by asset proxy")
    axis.set_ylabel("Value of EUR 1")
    axis.grid(alpha=0.25)
    axis.legend(ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_7_2_growth_of_one_euro.png", dpi=300)
    plt.close(fig)

    portfolio_names = list(MODEL_PORTFOLIOS)
    cagr = [performance[(name, "Annual")]["CAGR"] for name in portfolio_names]
    volatility = [
        performance[(name, "Annual")]["Annualised volatility"] for name in portfolio_names
    ]
    fig, axis = plt.subplots(figsize=(8, 6))
    axis.scatter(np.asarray(volatility) * 100, np.asarray(cagr) * 100, s=90, color="#164b85")
    for name, x_value, y_value in zip(portfolio_names, volatility, cagr):
        label_offset = (-58, 6) if name.startswith("Growth") else (6, 5)
        axis.annotate(
            name.split()[0],
            (x_value * 100, y_value * 100),
            xytext=label_offset,
            textcoords="offset points",
        )
    axis.set_xlabel("Annualised volatility (%)")
    axis.set_ylabel("CAGR (%)")
    axis.set_title("Annual-rebalanced model portfolios: realised risk and return")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_7_3_annual_risk_return.png", dpi=300)
    plt.close(fig)

    balanced = "Balanced 60/40"
    fig, axis = plt.subplots(figsize=(10, 6))
    for rule, color in [("Buy & Hold", "#b21f35"), ("Threshold", "#147f77")]:
        equity = simulations[(balanced, rule)]["pre_weights"][:, :2].sum(axis=1) * 100
        axis.plot(dates, equity, label=rule, color=color, linewidth=2)
    axis.axhline(60, color="#222222", linestyle="--", linewidth=1.4, label="60% target")
    axis.set_ylabel("Equity exposure (%)")
    axis.set_title("Balanced portfolio: equity exposure and allocation drift")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_7_4_balanced_equity_exposure.png", dpi=300)
    plt.close(fig)


def run_analysis(input_csv: Path, output_dir: Path) -> None:
    months, asset_returns, _ = load_monthly_returns(input_csv)
    if len(months) != 139:
        raise ValueError(f"Expected 139 monthly returns, found {len(months)}.")

    asset_rows: list[list] = []
    for column, ticker in enumerate(TICKERS):
        measures, _ = performance_metrics(asset_returns[:, column])
        asset_rows.append(
            [
                ticker,
                ASSET_NAMES[ticker],
                measures["CAGR"],
                measures["Annualised volatility"],
                measures["Maximum drawdown"],
                measures["Monthly VaR 95%"],
                measures["Monthly CVaR 95%"],
                measures["Positive months"],
                measures["Sharpe rf0"],
                measures["Sortino rf0"],
            ]
        )
    write_csv(
        output_dir,
        "asset_statistics.csv",
        [
            "Ticker",
            "Asset class",
            "CAGR",
            "Annualised volatility",
            "Max drawdown",
            "Monthly VaR95",
            "Monthly CVaR95",
            "Positive months",
            "Sharpe rf0",
            "Sortino rf0",
        ],
        asset_rows,
    )

    correlation = np.corrcoef(asset_returns, rowvar=False)
    write_csv(
        output_dir,
        "correlation_matrix.csv",
        ["Ticker", *TICKERS],
        [[ticker, *correlation[index].tolist()] for index, ticker in enumerate(TICKERS)],
    )

    simulations: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    performance: dict[tuple[str, str], dict[str, float]] = {}
    performance_rows: list[list] = []
    rebalance_rows: list[list] = []
    monthly_rows: list[list] = []

    for profile, target in MODEL_PORTFOLIOS.items():
        for rule in RULES:
            simulation = simulate(
                asset_returns,
                months,
                target,
                rule=rule,
                threshold=BASE_THRESHOLD,
                cost_bps=BASE_COST_BPS,
            )
            simulations[(profile, rule)] = simulation
            measures, _ = performance_metrics(
                simulation["returns"],
                simulation["turnovers"],
                simulation["rebalanced"],
                target,
                simulation["pre_weights"],
            )
            performance[(profile, rule)] = measures
            performance_rows.append(
                [
                    profile,
                    rule,
                    measures["CAGR"],
                    measures["Annualised volatility"],
                    measures["Maximum drawdown"],
                    measures["Average allocation drift"],
                    measures["Average annual turnover"],
                    measures["Number of rebalances"],
                    measures["Monthly VaR 95%"],
                    measures["Monthly CVaR 95%"],
                    measures["Final wealth"],
                ]
            )

            for index, ((year, month), flag) in enumerate(
                zip(months, simulation["rebalanced"])
            ):
                pre = simulation["pre_weights"][index]
                post = simulation["post_weights"][index]
                drift = 0.5 * float(np.sum(np.abs(pre - target)))
                monthly_rows.append(
                    [
                        f"{year:04d}-{month:02d}",
                        profile,
                        rule,
                        simulation["values"][index],
                        simulation["returns"][index],
                        float(pre[:2].sum()),
                        float(post[:2].sum()),
                        drift,
                        simulation["turnovers"][index],
                        simulation["costs"][index],
                        bool(flag),
                    ]
                )
                if flag:
                    rebalance_rows.append(
                        [
                            f"{year:04d}-{month:02d}",
                            profile,
                            rule,
                            simulation["turnovers"][index],
                            simulation["costs"][index],
                            drift,
                        ]
                    )

    write_csv(
        output_dir,
        "portfolio_performance.csv",
        [
            "Model portfolio",
            "Rule",
            "CAGR",
            "Annualised volatility",
            "Maximum drawdown",
            "Average allocation drift",
            "Average annual turnover",
            "Number of rebalances",
            "Monthly VaR95",
            "Monthly CVaR95",
            "Final wealth",
        ],
        performance_rows,
    )
    write_csv(
        output_dir,
        "monthly_portfolio_paths.csv",
        [
            "Month",
            "Model portfolio",
            "Rule",
            "Portfolio value",
            "Monthly return",
            "Pre-trade equity weight",
            "Post-trade equity weight",
            "Allocation drift",
            "Turnover",
            "Transaction cost",
            "Rebalanced",
        ],
        monthly_rows,
    )
    write_csv(
        output_dir,
        "rebalance_events.csv",
        ["Month", "Model portfolio", "Rule", "Turnover", "Transaction cost", "Pre-trade drift"],
        rebalance_rows,
    )

    ending_rows: list[list] = []
    for profile, target in MODEL_PORTFOLIOS.items():
        ending_rows.append(
            [
                profile,
                float(target[:2].sum()),
                *[
                    float(simulations[(profile, rule)]["post_weights"][-1, :2].sum())
                    for rule in RULES
                ],
            ]
        )
    write_csv(
        output_dir,
        "ending_equity_exposure.csv",
        ["Model portfolio", "Target equity", "Buy & Hold", "Annual", "Threshold"],
        ending_rows,
    )

    balanced = MODEL_PORTFOLIOS["Balanced 60/40"]
    cost_rows: list[list] = []
    for rule in ["Annual", "Threshold"]:
        for cost_bps in COST_SCENARIOS:
            simulation = simulate(
                asset_returns,
                months,
                balanced,
                rule,
                threshold=BASE_THRESHOLD,
                cost_bps=cost_bps,
            )
            measures, _ = performance_metrics(simulation["returns"])
            cost_rows.append([rule, cost_bps, measures["CAGR"], measures["Final wealth"]])
    write_csv(
        output_dir,
        "balanced_cost_sensitivity.csv",
        ["Rule", "Cost assumption (bps)", "CAGR", "Final wealth"],
        cost_rows,
    )

    threshold_rows: list[list] = []
    for threshold in THRESHOLD_SCENARIOS:
        simulation = simulate(
            asset_returns,
            months,
            balanced,
            "Threshold",
            threshold=threshold,
            cost_bps=BASE_COST_BPS,
        )
        measures, _ = performance_metrics(
            simulation["returns"],
            simulation["turnovers"],
            simulation["rebalanced"],
            balanced,
            simulation["pre_weights"],
        )
        threshold_rows.append(
            [
                threshold,
                measures["Number of rebalances"],
                measures["Average annual turnover"],
                measures["Average allocation drift"],
                measures["Maximum allocation drift"],
                measures["CAGR"],
            ]
        )
    write_csv(
        output_dir,
        "balanced_threshold_sensitivity.csv",
        ["Threshold", "Rebalances", "Average annual turnover", "Average drift", "Maximum drift", "CAGR"],
        threshold_rows,
    )

    stress_rows: list[list] = []
    covid_months = {(2020, 2), (2020, 3)}
    year_2020 = {(2020, month) for month in range(1, 13)}
    year_2022 = {(2022, month) for month in range(1, 13)}
    for profile in MODEL_PORTFOLIOS:
        strategy_returns = simulations[(profile, "Annual")]["returns"]
        stress_rows.append(
            [
                profile,
                period_return(strategy_returns, months, covid_months),
                period_return(strategy_returns, months, year_2020),
                period_return(strategy_returns, months, year_2022),
            ]
        )
    write_csv(
        output_dir,
        "historical_stress_periods.csv",
        ["Model portfolio", "Feb-Mar 2020", "Full-year 2020", "Full-year 2022"],
        stress_rows,
    )

    make_figures(output_dir, months, asset_returns, simulations, performance)

    print(f"Analysis complete: {len(months)} monthly observations.")
    print(f"Outputs written to: {output_dir.resolve()}")


if __name__ == "__main__":
    arguments = parse_args()
    run_analysis(arguments.input, arguments.output)
