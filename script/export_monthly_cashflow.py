import csv, os
from run_cashflow_predictor import _aggregate_monthly

os.makedirs("data", exist_ok=True)

res = _aggregate_monthly("data/transactions.csv")
monthly, debug = (res if isinstance(res, tuple) else (res, {}))

if not monthly:
    print(f"No monthly data. Debug: {debug}")
else:
    with open("data/monthly_cashflow.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month","income","expenses","net"])
        for m in sorted(monthly.keys()):
            row = monthly[m]
            w.writerow([m, row["income"], row["expenses"], row["net"]])
    print("Wrote data/monthly_cashflow.csv")
