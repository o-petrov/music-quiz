from urllib.request import urlopen, Request
from urllib.parse import urlencode
from time import sleep
import json

from src.database import database


def main():
    database.connect()

    # выборка песен без обновлённого года выпуска
    # мэтчим с MB по артистам и названию
    audios = database.audios.find({"first_release_MB": {"$exists": False}}, {"link": 1, "title": 1, "artists": 1})

    if not audios:
        print("Все года проставлены")
        return

    in_seconds = len(audios) + 1
    in_minutes, ss = in_seconds // 60, in_seconds % 60
    hh, mm = in_minutes // 60, in_minutes % 60
    print(f"Обновление годов для всех {len(audios)} треков с musicbrainz.org займёт {hh}:{mm:02}:{ss:02}")

    for audio in audios:
        query = urlencode({"query": audio["title"], "fmt": "json"})
        req = Request(  # MB требуют осмысленный UA с контактами
            'https://musicbrainz.org/ws/2/recording?' + query,
            headers={'User-Agent': 'Year updating script (pg7av4dsh at mozmail dot com)'}
        )
        
        with urlopen(req) as responce:
            html = responce.read()
        recs = json.loads(html)

        # фильтруем найденные записи по точному совпадению с названием и артистами
        # и берём дату/год выпуска
        def artists(rec):
            return set(credited["name"] for credited in rec["artist-credit"])
        releases = [
            r["first-release-date"] for r in recs["recordings"]
            if r["title"] == audio["title"] and artists(r) == set(audio["artists"])
        ]

        # так как даты мб вида '2023' и '2023-12-23' то просто сортируем алфавитно
        first_release = int(sorted(releases)[0][:4])
        # и записываем год в бд
        database.audios.update_one({"link": audio["link"]}, {"$set": {"first_release_MB": first_release}}, upsert=True)
        
        sleep(1)  # вроде надо не чаще раза в секунду с одного IP


if __name__ == '__main__':
    main()
