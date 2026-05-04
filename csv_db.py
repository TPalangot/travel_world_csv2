import csv
import os

BASE_PATH = "data"

def get_path(filename):
    return os.path.join(BASE_PATH, filename)

def read_csv(filename):
    path = get_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(filename, data, fieldnames):
    path = get_path(filename)
    with open(path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def append_csv(filename, row):
    path = get_path(filename)
    file_exists = os.path.exists(path)

    with open(path, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def generate_id(data):
    if not data:
        return "1"
    return str(max(int(row["id"]) for row in data) + 1)