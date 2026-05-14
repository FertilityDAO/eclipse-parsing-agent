"""Rank nations by longest and shortest total solar eclipse drought.

'Drought' = the longest gap (in years) between consecutive total solar
eclipses whose point of greatest eclipse falls within a country.

Caveat: uses point of greatest eclipse only, not the full shadow path.
Many eclipses peak over oceans, so land-based nations will have fewer
hits than reality. Still gives a useful relative ranking.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/eclipse_drought_by_nation.csv
"""

import csv
from pathlib import Path
from collections import defaultdict
import reverse_geocoder as rg

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "eclipse_drought_by_nation.csv"


def main():
    # Collect all total eclipses with coordinates
    eclipses = []
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            lat = float(row["lat_dd_ge"])
            lng = float(row["lng_dd_ge"])
            year = int(row["year"])
            eclipses.append({"year": year, "lat": lat, "lng": lng})

    print(f"Total eclipses to geocode: {len(eclipses)}")

    # Batch reverse geocode all points
    coords = [(e["lat"], e["lng"]) for e in eclipses]
    results = rg.search(coords)

    # Group eclipse years by country
    country_years = defaultdict(list)
    for e, geo in zip(eclipses, results):
        cc = geo["cc"]
        name = geo["admin1"] if "admin1" in geo else geo["name"]
        country_name = f"{cc}"
        country_years[cc].append(e["year"])

    # Get country names from results
    cc_to_name = {}
    for geo in results:
        if geo["cc"] not in cc_to_name:
            cc_to_name[geo["cc"]] = geo.get("cc", "Unknown")

    # Try to get proper country names
    try:
        # reverse_geocoder results have 'cc' (country code) - map to names
        import json
        # Build from the geo results themselves
        for geo in results:
            cc_to_name[geo["cc"]] = geo["cc"]
    except Exception:
        pass

    # Common country code to name mapping for readability
    CC_NAMES = {
        "US": "United States", "CN": "China", "RU": "Russia", "BR": "Brazil",
        "AU": "Australia", "IN": "India", "CA": "Canada", "ID": "Indonesia",
        "MX": "Mexico", "AR": "Argentina", "SA": "Saudi Arabia", "EG": "Egypt",
        "ZA": "South Africa", "NG": "Nigeria", "KE": "Kenya", "TR": "Turkey",
        "IR": "Iran", "IQ": "Iraq", "PK": "Pakistan", "JP": "Japan",
        "DE": "Germany", "FR": "France", "GB": "United Kingdom", "IT": "Italy",
        "ES": "Spain", "PT": "Portugal", "GR": "Greece", "SE": "Sweden",
        "NO": "Norway", "FI": "Finland", "PL": "Poland", "UA": "Ukraine",
        "RO": "Romania", "KZ": "Kazakhstan", "MN": "Mongolia", "MM": "Myanmar",
        "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines", "MY": "Malaysia",
        "CL": "Chile", "PE": "Peru", "CO": "Colombia", "VE": "Venezuela",
        "EC": "Ecuador", "BO": "Bolivia", "PY": "Paraguay", "UY": "Uruguay",
        "CU": "Cuba", "DO": "Dominican Republic", "HT": "Haiti",
        "GT": "Guatemala", "HN": "Honduras", "NI": "Nicaragua", "CR": "Costa Rica",
        "PA": "Panama", "JM": "Jamaica", "TT": "Trinidad and Tobago",
        "DZ": "Algeria", "LY": "Libya", "TN": "Tunisia", "MA": "Morocco",
        "SD": "Sudan", "TD": "Chad", "NE": "Niger", "ML": "Mali",
        "ET": "Ethiopia", "SO": "Somalia", "TZ": "Tanzania", "MZ": "Mozambique",
        "MG": "Madagascar", "AO": "Angola", "CD": "DR Congo", "CG": "Congo",
        "CM": "Cameroon", "GH": "Ghana", "CI": "Ivory Coast", "SN": "Senegal",
        "BF": "Burkina Faso", "GN": "Guinea", "SL": "Sierra Leone",
        "LR": "Liberia", "GA": "Gabon", "CF": "Central African Rep.",
        "MW": "Malawi", "ZM": "Zambia", "ZW": "Zimbabwe", "BW": "Botswana",
        "NA": "Namibia", "UG": "Uganda", "RW": "Rwanda", "BI": "Burundi",
        "ER": "Eritrea", "DJ": "Djibouti",
        "AF": "Afghanistan", "NP": "Nepal", "BD": "Bangladesh", "LK": "Sri Lanka",
        "KH": "Cambodia", "LA": "Laos", "SG": "Singapore",
        "NZ": "New Zealand", "PG": "Papua New Guinea", "FJ": "Fiji",
        "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "NL": "Netherlands",
        "CZ": "Czech Republic", "SK": "Slovakia", "HU": "Hungary",
        "RS": "Serbia", "HR": "Croatia", "BG": "Bulgaria", "AL": "Albania",
        "MK": "North Macedonia", "BA": "Bosnia and Herzegovina",
        "SI": "Slovenia", "ME": "Montenegro", "LT": "Lithuania",
        "LV": "Latvia", "EE": "Estonia", "BY": "Belarus", "MD": "Moldova",
        "GE": "Georgia", "AM": "Armenia", "AZ": "Azerbaijan",
        "TM": "Turkmenistan", "UZ": "Uzbekistan", "KG": "Kyrgyzstan",
        "TJ": "Tajikistan", "SY": "Syria", "JO": "Jordan", "LB": "Lebanon",
        "IL": "Israel", "PS": "Palestine", "YE": "Yemen", "OM": "Oman",
        "AE": "UAE", "QA": "Qatar", "BH": "Bahrain", "KW": "Kuwait",
        "KR": "South Korea", "KP": "North Korea", "TW": "Taiwan",
        "GL": "Greenland", "IS": "Iceland", "IE": "Ireland", "DK": "Denmark",
    }

    def get_name(cc):
        return CC_NAMES.get(cc, cc)

    # Compute droughts per country
    nation_stats = []
    for cc, years in country_years.items():
        years_sorted = sorted(years)
        count = len(years_sorted)
        if count < 2:
            max_gap = None
            avg_gap = None
        else:
            gaps = [years_sorted[i+1] - years_sorted[i] for i in range(len(years_sorted)-1)]
            max_gap = max(gaps)
            avg_gap = sum(gaps) / len(gaps)

        # Current drought: years since last eclipse (relative to dataset end ~3000)
        first_year = years_sorted[0]
        last_year = years_sorted[-1]

        nation_stats.append({
            "cc": cc,
            "name": get_name(cc),
            "count": count,
            "first": first_year,
            "last": last_year,
            "max_gap": max_gap,
            "avg_gap": avg_gap,
        })

    # Filter to countries with at least 2 eclipses (need gaps to compute drought)
    with_gaps = [n for n in nation_stats if n["max_gap"] is not None]
    by_longest = sorted(with_gaps, key=lambda x: x["max_gap"], reverse=True)
    by_shortest = sorted(with_gaps, key=lambda x: x["max_gap"])

    # Write full output
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank_longest", "country", "cc", "eclipse_count",
                         "longest_drought_yrs", "avg_gap_yrs", "first_eclipse", "last_eclipse"])
        for rank, n in enumerate(by_longest, 1):
            writer.writerow([rank, n["name"], n["cc"], n["count"],
                             n["max_gap"], f"{n['avg_gap']:.0f}",
                             n["first"], n["last"]])

    # Print results
    print(f"\nCountries with total eclipses (>=2): {len(with_gaps)}")
    single = [n for n in nation_stats if n["max_gap"] is None]
    print(f"Countries with only 1 eclipse: {len(single)}\n")

    print("=== TOP 15: LONGEST Eclipse Drought (biggest gap between consecutive eclipses) ===")
    print("Rank | Country                  | Eclipses | Longest Gap | Avg Gap | First  | Last")
    print("-----|--------------------------|----------|-------------|---------|--------|------")
    for rank, n in enumerate(by_longest[:15], 1):
        print(f" {rank:>2}  | {n['name']:<24} | {n['count']:>8} | {n['max_gap']:>7} yrs | {n['avg_gap']:>4.0f} yr | {n['first']:>6} | {n['last']:>5}")

    print("\n=== TOP 15: SHORTEST Eclipse Drought (smallest max gap) ===")
    print("Rank | Country                  | Eclipses | Longest Gap | Avg Gap | First  | Last")
    print("-----|--------------------------|----------|-------------|---------|--------|------")
    for rank, n in enumerate(by_shortest[:15], 1):
        print(f" {rank:>2}  | {n['name']:<24} | {n['count']:>8} | {n['max_gap']:>7} yrs | {n['avg_gap']:>4.0f} yr | {n['first']:>6} | {n['last']:>5}")


if __name__ == "__main__":
    main()
