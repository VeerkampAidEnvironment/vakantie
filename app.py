from flask import Flask, render_template, jsonify, send_from_directory
import os, json
from datetime import timedelta

app = Flask(__name__)

VACATIONS_DIR = "vacations"

def load_vacations():
    vacations = []
    for folder in os.listdir(VACATIONS_DIR):
        v_path = os.path.join(VACATIONS_DIR, folder)
        #if not os.path.isdir(v_path):
        #    continue

        info_file = os.path.join(v_path, "info.json")
        #if not os.path.exists(info_file):
        #    continue

        with open(info_file) as f:
            data = json.load(f)

        data["folder"] = folder  # important for building URLs on index

        # Collect GPX files properly
        gpx_dir = os.path.join(v_path, "gpx")
        gpx_files = []
        if os.path.exists(gpx_dir):
            for activity in os.listdir(gpx_dir):
                activity_path = os.path.join(gpx_dir, activity)
                if not os.path.isdir(activity_path):
                    continue
                for gpx_file in os.listdir(activity_path):
                    if gpx_file.endswith(".gpx"):
                        gpx_files.append({
                            "activity": activity,
                            "filename": gpx_file
                        })

        data["gpx_files"] = gpx_files
        ### collect climbing data
        climbing_file = os.path.join(v_path, "climbing.json")
        if os.path.exists(climbing_file):
            with open(climbing_file) as f:
                climbing_data = json.load(f)
            data['climbing'] = climbing_data

        vacations.append(data)
    return vacations

from datetime import datetime

def parse_gpx_dates(filename):
    """
    Extract start_date and end_date from GPX filename.
    Example: 17-10-2021_20-10-2021.gpx
    """
    base = os.path.splitext(filename)[0]
    try:
        start_str, end_str = base.split("_")
        start_date = datetime.strptime(start_str, "%d-%m-%Y")
        end_date = datetime.strptime(end_str, "%d-%m-%Y")
        end_date = end_date + timedelta(days=1) - timedelta(microseconds=1)
        return start_date, end_date
    except Exception as e:
        print("Error parsing GPX dates:", filename, e)
        return None, None


from PIL import Image
from PIL.ExifTags import TAGS

def get_photo_date(photo_path):
    """
    Returns datetime object from photo EXIF DateTimeOriginal, or None if missing.
    """
    try:
        img = Image.open(photo_path)
        exif = img._getexif()
        if not exif:
            return None
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None



@app.route("/")
def index():
    return render_template("index.html")


from jinja2.runtime import Undefined
import math

def clean_json(obj):
    # Replace NaN, Undefined → None
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, Undefined):
        return None
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_json(v) for v in obj]
    return obj

@app.route("/api/vacations")
def api_vacations():
    vacations = load_vacations()
    cleaned = clean_json(vacations)
    return jsonify(cleaned)


@app.route("/vacation/<folder>")
def vacation_page(folder):

    info_path = os.path.join(VACATIONS_DIR, folder, "info.json")
    if not os.path.exists(info_path):
        return "Vacation not found", 404

    with open(info_path) as f:
        info = json.load(f)

    photos_dir = os.path.join(VACATIONS_DIR, folder, "photos")
    photos = []
    if os.path.exists(photos_dir):
        photos = [f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".png"))]

    gpx_dir = os.path.join(VACATIONS_DIR, folder, "gpx")
    gpx_files = []
    if os.path.exists(gpx_dir):
        for activity in os.listdir(gpx_dir):
            activity_path = os.path.join(gpx_dir, activity)
            if not os.path.isdir(activity_path):
                continue
            for gpx_file in os.listdir(activity_path):
                if gpx_file.endswith(".gpx"):
                    gpx_files.append({
                        "activity": activity,
                        "filename": gpx_file
                    })
    activity_ranges = []
    for gpx in gpx_files:
        if gpx["activity"] == "via_ferrata":
            activity_ranges.append({
                "activity": gpx["activity"],
                "start": None,
                "end": None
            })
        else:
            start, end = parse_gpx_dates(gpx['filename'])
            if start and end:
                activity_ranges.append({
                    "activity": gpx["activity"],
                    "start": start,
                    "end": end
                })

    photo_groups = {act["activity"]: [] for act in activity_ranges}
    photo_groups["Unassigned"] = []

    for photo in photos:
        photo_path = os.path.join(VACATIONS_DIR, folder, "photos", photo)
        photo_date = get_photo_date(photo_path)
        assigned = False
        if photo_date:
            for act in activity_ranges:
                if act["start"] and act["end"]:
                    if act["start"] <= photo_date <= act["end"]:
                        photo_groups[act["activity"]].append(photo)
                        assigned = True
                        break
        if not assigned:
            photo_groups["Unassigned"].append(photo)
    climbing_data = None
    climbing_file = os.path.join(VACATIONS_DIR, folder, "climbing.json")
    if os.path.exists(climbing_file):
        with open(climbing_file) as f:
            climbing_data = json.load(f)

    return render_template(
        "vacation.html",
        info=info,
        folder=folder,
        gpx_files=gpx_files,
        photo_groups=photo_groups,
        climbing=climbing_data
    )


@app.route("/vacation/<folder>/photos/<filename>")
def serve_photo(folder, filename):
    return send_from_directory(os.path.join(VACATIONS_DIR, folder, "photos"), filename)


@app.route("/vacation/<folder>/gpx/<activity>/<filename>")
def serve_gpx(folder, activity, filename):
    gpx_folder = os.path.join(VACATIONS_DIR, folder, "gpx", activity)
    if not os.path.exists(os.path.join(gpx_folder, filename)):
        return "File not found", 404
    return send_from_directory(gpx_folder, filename)

@app.route("/vacation/<folder>/geojson/<activity>/<filename>")
def serve_geojson(folder, activity, filename):
    # Absolute path
    geojson_folder = os.path.join(app.root_path, VACATIONS_DIR, folder, "geojson", activity)
    file_path = os.path.join(geojson_folder, filename)

    if not os.path.exists(file_path):
        # Debug: log the full path
        print("GeoJSON not found at:", file_path)
        return "GeoJSON not found", 404

    return send_from_directory(geojson_folder, filename)


if __name__ == "__main__":
    app.run(debug=True)
