import os
import subprocess
import uuid

VACATIONS_DIR = "vacations"

def normalize(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(" ", "_")
    )

def git_mv(src, dst):
    subprocess.check_call(["git", "mv", src, dst])

def main():
    for vacation in os.listdir(VACATIONS_DIR):
        vac_path = os.path.join(VACATIONS_DIR, vacation)
        geojson_root = os.path.join(vac_path, "geojson")

        if not os.path.isdir(geojson_root):
            continue

        for activity in os.listdir(geojson_root):
            old_path = os.path.join(geojson_root, activity)
            if not os.path.isdir(old_path):
                continue

            new_name = normalize(activity)
            if new_name == activity:
                continue

            new_path = os.path.join(geojson_root, new_name)

            tmp_name = f"__tmp__{uuid.uuid4().hex[:6]}"
            tmp_path = os.path.join(geojson_root, tmp_name)

            print(f"\n{old_path}")
            print(f"  → {tmp_path}")
            print(f"  → {new_path}")

            git_mv(old_path, tmp_path)
            git_mv(tmp_path, new_path)

if __name__ == "__main__":
    main()
