import pandas as pd
import calendar

df = pd.read_csv("data/nasa_5millennium_solar_eclipses.csv")

# Keep total solar eclipses only
t = df[df["eclipse_type"] == "T"].copy()

# Build readable month-day labels
t["month_day"] = t.apply(
    lambda r: f"{calendar.month_abbr[int(r['month'])]} {int(r['day'])}",
    axis=1
)

# Build day-of-year values using leap year 2000
dates = pd.to_datetime(
    "2000-"
    + t["month"].astype(int).astype(str).str.zfill(2)
    + "-"
    + t["day"].astype(int).astype(str).str.zfill(2),
    format="%Y-%m-%d",
    errors="coerce",
)
t["day_of_year"] = dates.dt.dayofyear

month_day_counts = t["month_day"].value_counts().reset_index()
month_day_counts.columns = ["month_day", "count"]

doy_counts = t["day_of_year"].value_counts().reset_index()
doy_counts.columns = ["day_of_year", "count"]

month_day_counts.to_csv("outputs/total_eclipse_month_day_counts.csv", index=False)
doy_counts.to_csv("outputs/total_eclipse_day_of_year_counts.csv", index=False)

print("Top month-day combinations:")
print(month_day_counts.head(15).to_string(index=False))

print("\nTop day-of-year values:")
print(doy_counts.head(15).to_string(index=False))