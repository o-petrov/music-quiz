from urllib.request import urlopen, Request
from urllib.parse import urlencode
from time import sleep
import json
import re
import unicodedata

from src.database import database


tracks_not_found = []


def norm(name):
    # убираем странные пробелы и регистр
    name = re.sub(r"\s+", " ", name).strip().lower()
    # убираем диакритику
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')

    surname1 = re.findall(r"^(\w\.\s*)+(\w\w\w+)$", name)
    surname2 = re.findall(r"^(\w\w\w+)(\s*\w\.)+$", name)
    if surname1:  # [(last initial, surname)]
        return {name, surname1[0][1]}
    elif surname2:  # [(surname, last initial)]
        return {name, surname2[0][0]}

    alts = re.findall(r"\(([^)]*)\)", name)
    alts += re.findall(r"\[([^]]*)]", name)
    alts += re.findall(r'"([^"]*)"', name)
    alts += re.findall(r'«([^»]*)»', name)
    if len(alts) > 1:
        print(name, "has many alts")
    bare_name = re.sub(r"\(.*\)", "", name)
    bare_name = re.sub(r"\[.*]", "", bare_name)
    bare_name = re.sub(r'".*"', "", bare_name)
    bare_name = re.sub(r"«.*»", "", bare_name)

    # & может соединять двух артистов а может они всегда вместе
    names = [name] + bare_name.split('&') + bare_name.split('/') + bare_name.split(':') + alts
    names = set(names)

    # убираем всю пунктуацию и регистр
    wo_punct = set()
    for n in names:
        # просто склеиваем на месте странных символов
        wo_punct.add(re.sub(r"[^\w ]+", "", n).strip())
        # не склеиваем слова на месте странных символов
        wo_punct.add(re.sub(r"\W+", " ", n).strip())
        # не убираем -.'
        wo_punct.add(re.sub(r"[^\w.'-]+", " ", n).strip())

    if {"мот", "mot"} & wo_punct:
        wo_punct.update({"мот", "mot"})
    if "nyusha" in wo_punct:
        wo_punct.add("нюша")
    return wo_punct


def am2(rec, audio):
    audio_artists = [norm(credit["name"]) for credit in audio["artists"]]
    rec_artists = []
    for credit in rec["artist-credit"]:
        rec_artists.append(norm(credit["artist"]["name"]))
        rec_artists[-1].update(norm(credit["name"]))

    matched_r = any(any(
        r_name in a_name or a_name in r_name
        for r_name in r_names
        for a_names in audio_artists
        for a_name in a_names
    ) for r_names in rec_artists)
    matched_a = any(any(
        r_name in a_name or a_name in r_name
        for a_name in a_names
        for r_names in rec_artists
        for r_name in r_names
    ) for a_names in audio_artists)

    return matched_a and matched_r


def title_for_search(name):
    # убираем всё что в скобках
    # да, бывают альт.названия и названия через :-/ но забудем про это для простоты сравнения названий
    bare_name = re.sub(r"\(.*\)", "", name)
    bare_name = re.sub(r"\[.*]", "", bare_name)
    bare_name = re.sub(r'".*"', "", bare_name)
    bare_name = re.sub(r"«.*»", "", bare_name)
    # убираем всю пунктуацию и регистр (кроме '-)
    bare_name = re.sub(r"[^\w'-]+", " ", bare_name).strip().lower()
    # убираем диакритику
    bare_name = ''.join(c for c in unicodedata.normalize('NFD', bare_name) if unicodedata.category(c) != 'Mn')
    return bare_name


def tm2(rec, audio):
    rt = title_for_search(rec["title"])
    at = title_for_search(audio["track"])
    return rt == at or rt + ' ' + rt == at or at + ' ' + at == rt


def try_update_year(audio):
    artists = set()
    for credit in audio["artists"]:
        artists.update(norm(credit["name"]))
    artists = "(" + " OR ".join(f'artistname:"{n}"' for n in artists) + ")"
    recording = "recording:\"" + title_for_search(audio["track"]) + "\""
    query = urlencode({"query": recording + " AND " + artists, "fmt": "json"})
    req = Request(  # MB требуют осмысленный UA с контактами
        "https://musicbrainz.org/ws/2/recording?" + query,
        headers={"User-Agent": "Year updating script (pg7av4dsh at mozmail dot com)"}
    )

    with urlopen(req) as responce:
        html = responce.read()
    recordings = json.loads(html)["recordings"]
    # в выдаче может быть совсем не то...
    releases = [r for r in recordings if tm2(r, audio) and am2(r, audio)]
    if not any("first-release-date" in r for r in releases):
        # в фильтрованной выдаче нет инфы
        tracks_not_found.append(audio)
        return

    releases.sort(key=lambda r: r.get("first-release-date", "2900"))
    first_release = int(releases[0]["first-release-date"][:4])
    database.audios.update_one(
        {"link": audio["link"]},
        {"$set": {"release_year": min(first_release, audio["year"])}},
        upsert=True
    )

    if audio["year"] < first_release - 1:
        return

    rm, rt, am, at = am2(releases[0], audio, count=True)
    if rm == rt and am == at:
        return

    # возможно сейчас в библиотеке микс
    # TODO попробовать автоматически найти версию в яме
    return


def main():
    database.connect()

    # выборка песен без обновлённого года выпуска
    # мэтчим с MB по артистам и названию
    audios = database.audios.find({"release_year": {"$exists": False}}, {"link": 1, "title": 1, "artists": 1})

    if not audios:
        print("Все года проставлены")
        return

    in_seconds = len(audios) + 1
    in_minutes, ss = in_seconds // 60, in_seconds % 60
    hh, mm = in_minutes // 60, in_minutes % 60
    print(f"Обновление годов для всех {len(audios)} треков с musicbrainz.org займёт {hh}:{mm:02}:{ss:02}")

    for audio in audios:
        sleep(1)  # вроде надо не чаще раза в секунду с одного IP
        try_update_year(audio)


if __name__ == '__main__':
    main()
