import pandas as pd

df = pd.read_csv("data/nasa_5millennium_solar_eclipses.csv")

# Focus on Aug 12 only
aug12 = df[(df["month"] == 8) & (df["day"] == 12)].copy()

print("\nALL eclipse records on Aug 12:")
print(aug12[["year", "month", "day", "eclipse_type", "saros", "gamma", "magnitude"]].to_string(index=False))

print("\nCount by eclipse_type for Aug 12:")
print(aug12["eclipse_type"].value_counts().to_string())

# Strict total only
strict_total = aug12[aug12["eclipse_type"] == "T"].copy()
print("\nStrict total-only (eclipse_type == 'T') count:")
print(len(strict_total))

if len(strict_total) > 0:
    print(strict_total[["year", "month", "day", "eclipse_type", "saros", "gamma", "magnitude"]].to_string(index=False))

# Any type containing T
contains_t = aug12[aug12["eclipse_type"].astype(str).str.contains("T", na=False)].copy()
print("\nAny eclipse_type containing 'T' count:")
print(len(contains_t))

if len(contains_t) > 0:
    print(contains_t[["year", "month", "day", "eclipse_type", "saros", "gamma", "magnitude"]].to_string(index=False))