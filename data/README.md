# Data

The analysis expects the original Koyfin export to be placed at:

```text
data/raw/koyfin_2026-08-12-3.csv
```

The required columns are `Date` and the fields labelled `Adj. Close` for EUNL,
IQQE, XGLE, EUN5 and IBCI. The script uses the final valid daily observation in
each calendar month and evaluates January 2015 through July 2026.

The raw vendor export is intentionally excluded from the public repository.
Check the vendor's redistribution terms before sharing it. The README should
describe these observations as **Koyfin-adjusted prices** unless the vendor's
corporate-action and cash-distribution methodology has been independently
verified and archived.
