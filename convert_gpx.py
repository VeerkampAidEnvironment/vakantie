import os
import json
import gpxpy
from pathlib import Path

VACATIONS_DIR = Path("vacations")

# Simplification: keep every Nth point
SIMPLIFY_BY_ACTIVITY = {
    "Fietsen": 10,      # keep every 5th point
}

DEFAULT_SIMPLIFY = 1  # everything else

def convert_gpx(gpx_path: Path, out_path: Path, simplify_every: int):
    try:
        with open(gpx_path, "r", encoding="utf-8", errors="replace") as f:
            gpx = gpxpy.parse(f)
    except Exception as e:
        print(f"❌ Failed to parse {gpx_path}: {e}")
        return


    features = []

    for track in gpx.tracks:
        for seg in track.segments:
            coords = [
                [p.longitude, p.latitude]
                for i, p in enumerate(seg.points)
                if i % simplify_every == 0
            ]

            if len(coords) < 2:
                continue

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "source": "gpx",
                    "points_original": len(seg.points),
                    "points_simplified": len(coords)
                }
            })

    if not features:
        print(f"⚠️ No geometry in {gpx_path}")
        return

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    print(f"✅ {gpx_path} → {out_path}")

def run():
    print("🔍 Scanning vacations folder...")

    for vacation in VACATIONS_DIR.iterdir():
        gpx_root = vacation / "gpx"
        if not gpx_root.exists():
            continue

        geojson_root = vacation / "geojson"

        for activity in gpx_root.iterdir():

            simplify_every = SIMPLIFY_BY_ACTIVITY.get(
                activity.name,
                DEFAULT_SIMPLIFY
            )

            for gpx_file in activity.glob("*.gpx"):
                out_file = (
                        geojson_root /
                        activity.name /
                        (gpx_file.stem + ".json")
                )

                convert_gpx(gpx_file, out_file, simplify_every)

    print("🎉 Done")

if __name__ == "__main__":
    run()
