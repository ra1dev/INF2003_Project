## dont need to care about this fike, just script to update player images from TheSportsDB API, 
## using the player name to search and update the database with the new image URLs and sportsdb player ID. 

import time
import requests
import psycopg2
from urllib.parse import quote


DB_NAME = "epl_db_2"
DB_USER = "postgres"
DB_PASSWORD = "Password"
DB_HOST = "localhost"
DB_PORT = "5432"

SPORTSDB_API_KEY = "123"
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_API_KEY}/searchplayers.php"


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def search_sportsdb_player(player_name):
    url = f"{BASE_URL}?p={quote(player_name)}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 429:
            print(f"Rate limited. Waiting 60 seconds before retrying: {player_name}")
            time.sleep(60)

            response = requests.get(url, timeout=10)

            if response.status_code == 429:
                print(f"Still rate limited. Skipping for now: {player_name}")
                return None

        response.raise_for_status()
        data = response.json()

    except Exception as error:
        print(f"API error for {player_name}: {error}")
        return None

    results = data.get("player")

    if not results:
        return None

    for player in results:
        sport = (player.get("strSport") or "").lower()

        if sport == "soccer":
            return player

    return results[0]


def main():
    print("Script started")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT player_id, player_name
        FROM player
        WHERE player_image IS NULL
           OR TRIM(player_image) = ''
           OR player_image ILIKE '%ui-avatars%'
           OR player_photo_url IS NULL
           OR TRIM(player_photo_url) = ''
           OR player_photo_url ILIKE '%ui-avatars%'
        ORDER BY player_name;
    """)

    players = cur.fetchall()

    print(f"Players without valid images: {len(players)}")

    updated_count = 0
    not_found_count = 0

    for player_id, player_name in players:
        print(f"Searching: {player_name}")

        sportsdb_player = search_sportsdb_player(player_name)

        if not sportsdb_player:
            print("  Not found")
            not_found_count += 1
            time.sleep(5)
            continue

        sportsdb_player_id = sportsdb_player.get("idPlayer")

        image_url = (
            sportsdb_player.get("strCutout")
            or sportsdb_player.get("strThumb")
            or sportsdb_player.get("strRender")
            or sportsdb_player.get("strFanart1")
        )

        if not image_url:
            print("  Found player, but no image")
            not_found_count += 1
            time.sleep(5)
            continue

        cur.execute("""
            UPDATE player
            SET
                player_image = %s,
                player_photo_url = %s,
                sportsdb_player_id = %s,
                player_photo_source = 'TheSportsDB'
            WHERE player_id = %s;
        """, (image_url, image_url, sportsdb_player_id, player_id))

        conn.commit()

        updated_count += 1

        print(f"  Updated: {player_name}")
        print(f"  Image: {image_url}")

        time.sleep(5)

    cur.close()
    conn.close()

    print("Done.")
    print(f"Updated: {updated_count}")
    print(f"Not found / no image: {not_found_count}")


if __name__ == "__main__":
    main()