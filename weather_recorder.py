#!/usr/bin/env python3
"""
WeatherWorld Auto-Recorder
==========================
Fetches live weather for 12 world cities every time it runs.
Scheduled hourly by GitHub Actions — no PC needed.

Saves to:  weather_data/YYYY-MM-DD.csv   (daily file)
           weather_data/all_records.csv   (master CSV)
           weather_data/records.json      (dashboard reads this)
           weather_data/recorder.log      (activity log)

No third-party packages required — uses Python standard library only.
"""

import json, csv, urllib.request, urllib.parse, os
from datetime import datetime
from pathlib import Path

# ── 12 world cities ──────────────────────────────────────────────────────
CITIES = [
    {"name":"New York",    "country":"United States", "lat":40.7128, "lon":-74.0060},
    {"name":"London",      "country":"United Kingdom","lat":51.5074, "lon":-0.1278},
    {"name":"Tokyo",       "country":"Japan",         "lat":35.6762, "lon":139.6503},
    {"name":"Sydney",      "country":"Australia",     "lat":-33.8688,"lon":151.2093},
    {"name":"Dubai",       "country":"UAE",           "lat":25.2048, "lon":55.2708},
    {"name":"Paris",       "country":"France",        "lat":48.8566, "lon":2.3522},
    {"name":"Singapore",   "country":"Singapore",     "lat":1.3521,  "lon":103.8198},
    {"name":"Los Angeles", "country":"United States", "lat":34.0522, "lon":-118.2437},
    {"name":"Mumbai",      "country":"India",         "lat":19.0760, "lon":72.8777},
    {"name":"Cairo",       "country":"Egypt",         "lat":30.0444, "lon":31.2357},
    {"name":"Sao Paulo",   "country":"Brazil",        "lat":-23.5505,"lon":-46.6333},
    {"name":"Moscow",      "country":"Russia",        "lat":55.7558, "lon":37.6173},
]

CSV_HEADERS = [
    "Timestamp","City","Country","Latitude","Longitude",
    "Temp_C","Temp_F","FeelsLike_C","FeelsLike_F",
    "Humidity_%","Wind_kmh","Wind_Dir","Wind_Deg",
    "Rain_mm","UV_Index","Pressure_hPa",
    "CloudCover_%","Visibility_km","Condition","WMO_Code"
]

WMO = {
    0:"Clear Sky",1:"Mainly Clear",2:"Partly Cloudy",3:"Overcast",
    45:"Foggy",48:"Icy Fog",
    51:"Light Drizzle",53:"Drizzle",55:"Heavy Drizzle",
    61:"Light Rain",63:"Rain",65:"Heavy Rain",
    71:"Light Snow",73:"Snow",75:"Heavy Snow",77:"Snow Grains",
    80:"Light Showers",81:"Rain Showers",82:"Heavy Showers",
    85:"Snow Showers",95:"Thunderstorm",96:"Thunderstorm",99:"Thunderstorm",
}

OUT = Path("weather_data")

def c2f(c):  return round(c * 9/5 + 32, 1)
def wdir(d): return ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                     'S','SSW','SW','WSW','W','WNW','NW','NNW'][round((d or 0)/22.5)%16]

def fetch_city(lat, lon):
    params = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "current": ("temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,rain,weather_code,wind_speed_10m,"
                    "wind_direction_10m,cloud_cover,surface_pressure,"
                    "uv_index,visibility"),
        "timezone": "auto"
    })
    url = "https://api.open-meteo.com/v1/forecast?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "WeatherWorld/2.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def append_csv(path, rows, write_header):
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(CSV_HEADERS)
        w.writerows(rows)

def main():
    now      = datetime.now()
    ts       = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")

    OUT.mkdir(exist_ok=True)

    daily_csv  = OUT / f"{date_str}.csv"
    master_csv = OUT / "all_records.csv"
    json_store = OUT / "records.json"
    log_file   = OUT / "recorder.log"

    rows_csv  = []
    rows_json = []

    print(f"\n{'='*54}")
    print(f"  WeatherWorld Recorder  |  {ts}")
    print(f"{'='*54}")

    for city in CITIES:
        pad = f"  {city['name']:<16}"
        try:
            d  = fetch_city(city["lat"], city["lon"])
            cv = d["current"]

            t_c   = round(cv["temperature_2m"])
            fl_c  = round(cv["apparent_temperature"])
            wdeg  = int(cv.get("wind_direction_10m") or 0)
            wkm   = round(cv.get("wind_speed_10m")   or 0)
            rain  = round(float(cv.get("rain")        or 0), 2)
            hum   = int(cv.get("relative_humidity_2m") or 0)
            pres  = round(cv.get("surface_pressure")   or 0)
            cloud = int(cv.get("cloud_cover")          or 0)
            vis_r = cv.get("visibility")
            vis   = round(vis_r / 1000, 1) if vis_r is not None else None
            uv_r  = cv.get("uv_index")
            uv    = round(uv_r) if uv_r is not None else None
            code  = int(cv.get("weather_code") or 0)
            cond  = WMO.get(code, "Unknown")

            rows_csv.append([
                ts, city["name"], city["country"],
                city["lat"], city["lon"],
                t_c, c2f(t_c), fl_c, c2f(fl_c),
                hum, wkm, wdir(wdeg), wdeg,
                rain, uv if uv is not None else "",
                pres, cloud,
                vis  if vis is not None else "",
                cond, code
            ])
            rows_json.append({
                "id":    f"{int(now.timestamp())}_{city['name'].replace(' ','')}",
                "dt":    ts,
                "city":  city["name"],  "ctry": city["country"],
                "lat":   city["lat"],   "lon":  city["lon"],
                "temp":  t_c,  "feels": fl_c,
                "hum":   hum,  "wind":  wkm,
                "wdir":  wdir(wdeg), "wdeg": wdeg,
                "rain":  rain, "uv":    uv,
                "pres":  pres, "cloud": cloud,
                "vis":   vis,  "cond":  cond, "code": code
            })
            print(f"{pad}  {t_c:>4}°C  {cond}")

        except Exception as e:
            print(f"{pad}  [FAILED] {e}")

    if not rows_csv:
        print("\n  No data recorded — check internet connection.")
        return

    # Daily CSV
    append_csv(daily_csv, rows_csv, not daily_csv.exists())

    # Master CSV
    append_csv(master_csv, rows_csv, not master_csv.exists())

    # JSON store (newest first, capped at 50 000 records)
    existing = []
    if json_store.exists():
        try:
            with open(json_store, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    combined = rows_json + existing
    if len(combined) > 50000:
        combined = combined[:50000]
    with open(json_store, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, separators=(",", ":"))

    # Activity log
    total_rows = sum(1 for _ in open(master_csv, encoding="utf-8")) - 1
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}]  OK  {len(rows_csv):>2} cities  "
                f"daily={daily_csv.name}  master={total_rows} rows  "
                f"json={len(combined)} records\n")

    print(f"\n  Saved → {OUT}/")
    print(f"  Daily : {daily_csv.name}  |  Master : {total_rows} rows  |  JSON : {len(combined)} records")
    print(f"{'='*54}\n")

if __name__ == "__main__":
    main()
