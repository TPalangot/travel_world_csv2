import csv
import os

BASE_DIR = "data"

# Ensure folder exists
os.makedirs(BASE_DIR, exist_ok=True)

def create_csv(filename, headers):
    path = os.path.join(BASE_DIR, filename)

    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"✅ Created {filename}")
    else:
        print(f"ℹ️ {filename} already exists")

def init_csv_db():
    create_csv("users.csv", [
        "id","first_name","last_name","contact","email","password","role","created_at"
    ])

    create_csv("destinations.csv", [
        "id","name","type","description","image","created_at"
    ])

    create_csv("places.csv", [
        "id","destination_id","name","district","description","map_link","image",
        "things_to_do","best_time_from","best_time_to","created_at"
    ])

    create_csv("visited_places.csv", [
        "id","user_id","place_id","visited_at"
    ])

    create_csv("trips.csv", [
        "id","user_id","title","trip_type","estimated_budget",
        "start_date","end_date","created_at"
    ])

    create_csv("trip_days.csv", [
        "id","trip_id","day_number","created_at"
    ])

    create_csv("trip_places.csv", [
        "id","trip_day_id","place_id","place_name","things_to_do",
        "food","things_to_buy","time_to_spend","distance_to_next",
        "time_to_next","notes","created_at"
    ])

    create_csv("completed_trips.csv", [
        "id","user_id","title","description","visit_date","budget",
        "google_drive_link","title_image","created_at"
    ])

    create_csv("completed_trip_places.csv", [
        "id","completed_trip_id","place_id","created_at"
    ])

    create_csv("people_met.csv", [
        "id","completed_trip_id","name","contact","email","image","created_at"
    ])

if __name__ == "__main__":
    init_csv_db()