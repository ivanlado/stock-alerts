import { formatCompact, formatNumber, formatPercent } from "./format";
import type { CompanyCard } from "./types";

/**
 * The numbers Search shows and filters on, each with how to write it and a
 * plain-words explanation for the "i" button.
 *
 * Declared once so a table column and a filter box about the same metric
 * cannot disagree on its label, its unit or what it means. The explanations
 * are written for someone who does not follow the stock market: short, no
 * jargon, and with a rule of thumb for what a good or bad value looks like.
 */
export type Metric = {
  label: string;
  unit: "ratio" | "percent" | "money";
  value: (c: CompanyCard) => number | null;
  info: string;
  /**
   * Below zero the number means something else, not "cheaper": a negative PER
   * is a company losing money. A range filter on such a metric leaves those
   * rows out, so "PER up to 15" does not return loss-makers.
   */
  positiveOnly?: boolean;
};

/** How a metric's number is written, by unit. */
export function formatMetric(metric: Metric, value: number | null | undefined): string {
  if (metric.unit === "percent") return formatPercent(value);
  if (metric.unit === "money") return formatCompact(value);
  return formatNumber(value);
}

export const GAP: Metric = {
  label: "vs target",
  unit: "percent",
  value: (c) => c.pct_price_diff,
  info:
    "Today's price against the price analysts expect, on average. −20% means the " +
    "share trades 20% below what analysts think it is worth.",
};

export const PER: Metric = {
  label: "PER",
  unit: "ratio",
  value: (c) => c.trailing_pe,
  info:
    "Price ÷ profit per share. Roughly how many years of today's profit you pay " +
    "for when you buy the share. Lower is cheaper: about 15 is a classic " +
    "reference, above 30 is expensive unless profits grow fast. Negative means " +
    "the company is losing money; filtering on PER leaves those out.",
  positiveOnly: true,
};

export const PRICE_TO_SALES: Metric = {
  label: "Price / sales",
  unit: "ratio",
  value: (c) => c.price_to_sales,
  info:
    "The company's stock-market value ÷ its yearly sales. Useful when profits " +
    "are small or negative. Lower is cheaper; below 1–2 is often cheap, but it " +
    "varies a lot from one sector to another.",
  positiveOnly: true,
};

export const OPERATING_MARGIN: Metric = {
  label: "Operating margin",
  unit: "percent",
  value: (c) => c.fundamentals?.operating_margin ?? null,
  info:
    "Of every 100 the company sells, how much is left after paying for running " +
    "the business (before interest and taxes). Higher means a more profitable " +
    "business: 7% is the screener's minimum, above 20% is excellent.",
};

export const DEBT_TO_EQUITY: Metric = {
  label: "Debt / equity",
  unit: "ratio",
  value: (c) => c.fundamentals?.debt_to_equity ?? null,
  info:
    "Debt divided by the shareholders' own money. 1 means the company owes as " +
    "much as its shareholders have put in. Lower is safer: the screener asks " +
    "for 1 or less, above 2 is a lot of debt. Negative means the shareholders' " +
    "money is below zero, which is not a good sign.",
};

export const CURRENT_RATIO: Metric = {
  label: "Current ratio",
  unit: "ratio",
  value: (c) => c.fundamentals?.current_ratio ?? null,
  info:
    "What the company has or will collect within a year (cash, money customers " +
    "owe it) ÷ what it must pay within a year. Above 1 means it can cover those " +
    "payments; below 1 can mean a cash squeeze.",
};

export const REVENUE: Metric = {
  label: "Revenue",
  unit: "money",
  value: (c) => c.fundamentals?.total_revenue ?? null,
  info:
    "Total sales in the last reported year, in the currency the company reports " +
    "in (B = billions, M = millions). It says how big the business is.",
};

export const REVENUE_GROWTH: Metric = {
  label: "Revenue growth",
  unit: "percent",
  value: (c) => c.revenue_growth,
  info:
    "How much sales grew in the last reported year against the year before. " +
    "Positive means the business is growing; negative, that it is shrinking. " +
    "A cheap company with falling sales may be cheap for a reason.",
};

export const FREE_CASH_FLOW: Metric = {
  label: "Free cash flow",
  unit: "money",
  value: (c) => c.fundamentals?.free_cash_flow ?? null,
  info:
    "Cash left in the last reported year after running the business and paying " +
    "for its investments. Harder to dress up than profit. Positive is good; " +
    "negative means the company burned cash.",
};
