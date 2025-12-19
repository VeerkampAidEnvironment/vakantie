import os
import json
import gpxpy
from pathlib import Path

VACATIONS_DIR = Path("vacations")

# Simplification: keep every Nth point
SIMPLIFY_EVERY = 10   # increase = faster & lighter

def convert_gpx(gpx_path: Path, out_path: Path):
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    features = []

    for track in gpx.tracks:
        for seg in track.segments:
            coords = [
                [p.longitude, p.latitude]
                for i, p in enumerate(seg.points)
                if i % SIMPLIFY_EVERY == 0
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
            if not activity.is_dir():
                continue

            for gpx_file in activity.glob("*.gpx"):
                out_file = (
                    geojson_root /
                    activity.name /
                    (gpx_file.stem + ".json")
                )

                # Skip if already converted
                if out_file.exists():
                    print(f"⏭️  Skipping existing {out_file}")
                    continue

                convert_gpx(gpx_file, out_file)

    print("🎉 Done")

if __name__ == "__main__":
    run()
