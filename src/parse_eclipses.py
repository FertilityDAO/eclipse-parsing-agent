import csv
from pathlib import Path

# File locations (relative to this script's directory)
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "eclipses_clean.csv"

ECLIPSE_TYPES = {
    "T": "Total", "Tm": "Total", "Tn": "Total", "Ts": "Total",
    "T+": "Total", "T-": "Total",
    "A": "Annular", "Am": "Annular", "An": "Annular", "As": "Annular",
    "A+": "Annular", "A-": "Annular",
    "H": "Hybrid", "Hm": "Hybrid", "H2": "Hybrid", "H3": "Hybrid",
    "P": "Partial", "Pb": "Partial", "Pe": "Partial",
}


def parse_duration(duration_str):
    """
    Convert NASA duration like '06m37s' to HH:MM:SS and total seconds.
    Returns (hms_string, seconds) or (None, None) for '00m00s'.
    """
    try:
        duration_str = duration_str.strip()
        if duration_str == "00m00s":
            return None, None
        parts = duration_str.replace("m", ":").replace("s", "").split(":")
        minutes, seconds = int(parts[0]), int(parts[1])
        total = minutes * 60 + seconds
        hms = f"00:{minutes:02d}:{seconds:02d}"
        return hms, total
    except (ValueError, IndexError):
        return None, None


def build_date(year, month, day):
    """
    Build a date string from year, month, day.
    Handles negative (BCE) years with a minus sign prefix.
    """
    y = int(year)
    m = int(month)
    d = int(day)
    if y < 0:
        return f"-{abs(y):04d}-{m:02d}-{d:02d}"
    return f"{y:04d}-{m:02d}-{d:02d}"


def main():
    cleaned_rows = []

    with open(INPUT_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            duration_hms, duration_seconds = parse_duration(row["central_duration"])

            cleaned_rows.append({
                "date": build_date(row["year"], row["month"], row["day"]),
                "type": ECLIPSE_TYPES.get(row["eclipse_type"], row["eclipse_type"]),
                "duration_hms": duration_hms or "",
                "duration_seconds": duration_seconds if duration_seconds is not None else "",
                "latitude": row["lat_ge"],
                "longitude": row["lng_ge"],
                "latitude_numeric": row["lat_dd_ge"],
                "longitude_numeric": row["lng_dd_ge"],
                "saros_cycle": row["saros"],
                "gamma": row["gamma"],
                "magnitude": row["magnitude"],
                "path_width_km": row["path_width"],
            })

    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    with open(OUTPUT_FILE, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cleaned_rows[0].keys())
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"Clean dataset created: {OUTPUT_FILE}")
    print(f"Total eclipses: {len(cleaned_rows)}")


if __name__ == "__main__":
    main()
