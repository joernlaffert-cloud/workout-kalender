import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

CLUBS = {
    "1f7a56be-13c6-47cf-a4f5-70b9e32ae30c": "Workout Juliusstraße",
    "e428e667-c6d7-4fcb-8328-a52b8e19041d": "Workout Wasserwelt"
}

def fetch_courses(club_id):
    url = "https://icm01f02d27fd55f3.clubkonzepte24.de:33929/booking/kursplan/week"
    # Fetch from now up to 2 weeks back and 2 weeks forward to be safe
    today = datetime.now(timezone.utc)
    start_date = today - timedelta(days=today.weekday()) - timedelta(days=7)
    end_date = start_date + timedelta(days=28)
    
    headers = {
        "clubid": club_id,
        "sid": "65d82d4e-d231-4c09-8e71-959256deae44",
        "Origin": "https://proxy.clubkonzepte24.de",
        "Referer": f"https://proxy.clubkonzepte24.de/courses/{club_id}/kursbuchung",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=utf-8"
    }
    
    payload = {
        "Start": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
        "Ende": end_date.strftime("%Y-%m-%dT00:00:00.000Z"),
        "Id": False,
        "CheckBuchbareKurse": False,
        "AnzahlWochenZumPruefen": None
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='PUT')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if "Daten" in res_data and "allKurse" in res_data["Daten"]:
                return res_data["Daten"]["allKurse"]
    except Exception as e:
        print(f"Error fetching data for {club_id}: {e}")
    return []

def generate_ics(all_courses_by_club, filename):
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Workout Braunschweig Kurse//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Workout Braunschweig",
        "X-WR-TIMEZONE:Europe/Berlin",
        "X-WR-CALDESC:Kursplan von Workout Braunschweig"
    ]
    
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    for club_id, courses in all_courses_by_club.items():
        club_name = CLUBS.get(club_id, "Workout")
        
        for course in courses:
            try:
                # "Start": "2024-05-13T08:00:00.000Z"
                start_dt = datetime.strptime(course["Start"], "%Y-%m-%dT%H:%M:%S.%fZ")
                start_dt = start_dt.replace(tzinfo=timezone.utc)
                
                end_dt = datetime.strptime(course["Ende"], "%Y-%m-%dT%H:%M:%S.%fZ")
                end_dt = end_dt.replace(tzinfo=timezone.utc)
                
                resources = course.get("Ressourcen", [])
                room = "Unbekannter Raum"
                instructor = "Unbekannter Trainer"
                
                for res in resources:
                    parts = res.split(",")
                    if len(parts) >= 3:
                        if parts[2] == "0":
                            room = parts[1]
                        elif parts[2] == "1":
                            instructor = parts[1]
                
                name = course.get("Bezeichnung", "Kurs").replace(",", "\\,").replace(";", "\\;")
                uid = f"workout-{club_id}-{course.get('Nr', '')}-{start_dt.strftime('%Y%m%dT%H%M%S')}@workout-bs.de"
                
                desc_raw = f"Trainer: {instructor}\\nRaum: {room}\\n{course.get('Infotext', '')}"
                desc = desc_raw.replace(chr(10), "\\n").replace("\r", "").replace(",", "\\,").replace(";", "\\;")
                
                ics_lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{dtstamp}",
                    f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}",
                    f"SUMMARY:[{club_name.replace('Workout ', '')}] {name}",
                    f"DESCRIPTION:{desc}",
                    f"LOCATION:{club_name}\\, Braunschweig",
                    "END:VEVENT"
                ])
            except Exception as e:
                print(f"Skipping course due to error: {e}")
                
    ics_lines.append("END:VCALENDAR")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(ics_lines))
    
    print(f"Successfully wrote ICS to {filename}")

if __name__ == "__main__":
    courses_by_club = {}
    for club_id, club_name in CLUBS.items():
        print(f"Fetching for {club_name}...")
        courses = fetch_courses(club_id)
        courses_by_club[club_id] = courses
        print(f"Found {len(courses)} courses.")
        
    generate_ics(courses_by_club, "workout_braunschweig_kurse.ics")
