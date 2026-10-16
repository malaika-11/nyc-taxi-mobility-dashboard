# Person 1: Taxi Demand Analysis Findings

## 1. Introduction

This analysis examines New York City yellow taxi pickup patterns in January 2019. It covers demand by hour, by day of the week, weekday versus weekend, and by calendar date. All figures come from the cleaned `trip` table, produced by `scripts/analyze_demand.py` and stored in `outputs/*.csv`.

> Verify before submitting: the figures below come from a run that analysed 7,524,401 trips. If your current `taxi.db` has a different trip count, re-run `python scripts/analyze_demand.py` and update the numbers (see the checklist at the end).

## 2. Hourly demand

- **Busiest hour:** 18:00, with 505,201 pickups.
- **Quietest hour:** 04:00, with 59,184 pickups. The busiest hour is about 8.5 times the quietest.
- **Key observation:** demand is driven by the evening, not the morning rush. Pickups climb from 72,626 at 05:00 to 365,805 at 08:00 and then stay on a plateau of roughly 350,000 to 370,000 through 11:00. They keep rising through the afternoon (441,511 at 15:00), peak at 18:00 and fall away after 21:00 (402,022) to 275,949 at 23:00.

## 3. Demand by day of the week

- **Busiest day by total pickups:** Thursday, 1,327,275.
- **Quietest day by total pickups:** Sunday, 840,871.
- **Average daily demand:** totals are misleading because January 2019 has five Tuesdays, Wednesdays and Thursdays but only four of each other day. Per day, **Friday is the busiest** (265,749 pickups per day) just ahead of Thursday (265,455), and Sunday is the quietest (210,218).

| Weekday | Total pickups | Days in January | Average per day |
|---|---|---|---|
| Monday | 887,614 | 4 | 221,904 |
| Tuesday | 1,180,763 | 5 | 236,153 |
| Wednesday | 1,236,344 | 5 | 247,269 |
| Thursday | 1,327,275 | 5 | 265,455 |
| Friday | 1,062,997 | 4 | 265,749 |
| Saturday | 988,537 | 4 | 247,134 |
| Sunday | 840,871 | 4 | 210,218 |

## 4. Weekday versus weekend demand

- **Total weekday pickups:** 5,694,993 (75.7% of all trips).
- **Total weekend pickups:** 1,829,408 (24.3%).
- **Key observation:** weekdays carry three quarters of the trips only because there are more of them (23 weekdays against 8 weekend days). Per day, a weekday averages 247,608 pickups and a weekend day 228,676, which is just 7.6% lower. Weekend demand is much stronger than the totals suggest.

## 5. Daily demand patterns

- **Highest-demand date:** Friday 25 January, with 286,286 pickups (Friday 11 January was close behind with 285,192).
- **Lowest-demand date:** Tuesday 1 January (New Year's Day), with 184,436 pickups.
- **Key observation:** the two lowest dates are public holidays. Monday 21 January (Martin Luther King Jr. Day) had 188,637 pickups, about 19% below the average of the other three Mondays (232,992). Commuter demand drops on holidays, so these dips are real behaviour and not bad data.

## 6. Conclusion

Taxi demand in January 2019 follows commuter and leisure rhythms: a long climb through the day, an evening peak at 18:00, the strongest days at the end of the working week, a smaller than expected weekend drop, and clear dips on public holidays. Comparing per-day averages instead of raw totals changes the answer to "which weekday is busiest".

## 7. Limitations

The analysis covers January 2019 only. Pickup counts measure recorded trip activity, not passenger waiting times or unmet demand. Weather, events and holidays are not in the data, so these results describe when demand changes but cannot alone explain why.

## Checklist: keeping these numbers correct

```bash
python scripts/analyze_demand.py      # regenerates outputs/*.csv from the current taxi.db
cat outputs/average_daily_demand.csv  # compare with the table in section 3
sqlite3 database/taxi.db "select count(*) from trip;"
```