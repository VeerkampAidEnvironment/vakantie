import os
import uuid

VACATIONS_DIR = "vacations"

def normalize(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(" ", "_")
    )

def force_rename(src, dst):
    if src == dst:
        return

    if os.path.normcase(src) == os.path.normcase(dst):
        # Case-only rename → use temp name
        tmp = src + "__tmp__" + uuid.uuid4().hex[:6]
        os.rename(src, tmp)
        os.rename(tmp, dst)
    else:
        os.rename(src, dst)

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
            new_path = os.path.join(geojson_root, new_name)

            if os.path.abspath(old_path) == os.path.abspath(new_path):
                continue

            print(f"Renaming: {old_path} → {new_path}")
            force_rename(old_path, new_path)

if __name__ == "__main__":
    main()
