import random
from collections import defaultdict
from typing import List, Tuple

from src import constants
from src.database import database
from src.dataclasses.settings import Settings
from src.utils.audio import contain_line, detect_chorus


def get_question_weights(settings: Settings, statistics: List[dict]) -> List[float]:
    if not statistics:
        return [1 for _ in settings.questions]

    question2count = defaultdict(int)

    for record in statistics:
        question2count[record["question_type"]] += 1

    return [1 / (question2count[question_type] + 1) for question_type in settings.questions]


def get_question_params(settings: Settings, username: str) -> Tuple[str, dict]:
    statistics = list(database.statistic.find(
        {"username": username, "question_type": {"$in": settings.questions}},
        {"link": 1, "question_type": 1, "correct": 1}
    ).sort("datetime", -1).limit(constants.QUESTION_STATISTICS_LIMIT))

    question_weights = get_question_weights(settings, statistics)
    question_type = random.choices(settings.questions, weights=question_weights, k=1)[0]

    last_links = [record["link"] for record in statistics if record["correct"] and record["question_type"] == question_type]
    incorrect_links = [record["link"] for record in statistics if not record["correct"] and record["question_type"] == question_type]
    links_query = {"$in": incorrect_links} if incorrect_links and random.random() < constants.REPEAT_PROBABILITY else {"$nin": last_links}

    query = {**settings.to_query(question_type), "link": links_query}
    audios = list(database.audios.find(query, {"link": 1, "_id": 0}))
    audio = database.audios.find_one({"link": random.choice(audios)["link"]})

    return question_type, audio


def get_chorus_question(lyrics: List[dict]) -> Tuple[int, int]:
    chorus_indices = detect_chorus(lyrics)
    start_index = 0
    available_indices = []

    for index in range(3, len(chorus_indices)):
        if not contain_line(lyrics, chorus_indices[start_index:index], lyrics[chorus_indices[index]]["text"]):
            available_indices.append(index)

    index = random.choice(available_indices)
    return chorus_indices[start_index], chorus_indices[index]


def get_question_title(question_type: str, audio: dict) -> str:
    artist = "исполнителя" if len(audio["artists"]) == 1 else "исполнителей"

    if question_type == constants.QUESTION_ARTIST_BY_TRACK:
        return f"назовите {artist} песни"

    if question_type == constants.QUESTION_ARTIST_BY_INTRO:
        return f"назовите {artist} песни по её вступлению"

    if question_type == constants.QUESTION_NAME_BY_TRACK:
        return "назовите название песни"

    if question_type == constants.QUESTION_LINE_BY_TEXT:
        return "продолжите строку"

    if question_type == constants.QUESTION_LINE_BY_CHORUS:
        return "продолжите строку припева"

    raise ValueError(f'Invalid question type "{question_type}"')


def make_question(audio: dict, question_type: str) -> dict:
    question = {
        "type": question_type,
        "title": get_question_title(question_type, audio)
    }

    artists = [artist["name"] for artist in audio["artists"]]
    lyrics: List[dict] = audio.get("lyrics", [])
    track_start = lyrics[0]["time"] if lyrics else ""
    seek_start = random.choice(lyrics[:len(lyrics) * 3 // 4])["time"] if lyrics else 0

    if question_type == constants.QUESTION_ARTIST_BY_TRACK:
        question["answer"] = artists
        question["answer_string"] = ", ".join([f'<a href="/artists/{artist["id"]}" target="_blank">{artist["name"]}</a>' for artist in audio["artists"]])
        question["question_timecode"] = track_start
        question["question_seek"] = seek_start
        question["answer_timecode"] = ""
    elif question_type == constants.QUESTION_ARTIST_BY_INTRO:
        question["answer"] = artists
        question["answer_string"] = ", ".join([f'<a href="/artists/{artist["id"]}" target="_blank">{artist["name"]}</a>' for artist in audio["artists"]])
        question["question_timecode"] = f'0,{round(lyrics[0]["time"] - 1, 2)}'
        question["answer_timecode"] = f'0,{round(lyrics[0]["time"] - 1, 2)}'
    elif question_type == constants.QUESTION_NAME_BY_TRACK:
        question["answer"] = audio["track"]
        question["question_timecode"] = track_start
        question["question_seek"] = seek_start
        question["answer_timecode"] = ""
    elif question_type == constants.QUESTION_LINE_BY_TEXT:
        index = random.randint(3, len(lyrics) - 2)
        start_time = round(max(0, lyrics[index - 3]["time"] - 0.8), 2)
        end_time = round(lyrics[index]["time"] - 0.3, 2)
        end_answer_time = f',{round(lyrics[index + 1]["time"] - 0.1, 2)}' if index + 1 < len(lyrics) else ""
        seek_answer_time = round(lyrics[index - 1]["time"], 2)

        question["text"] = [line["text"] for line in lyrics[index - 3:index]]
        question["answer"] = lyrics[index]["text"]
        question["question_timecode"] = f"{start_time},{end_time}"
        question["answer_timecode"] = f"{start_time}{end_answer_time}"
        question["answer_seek"] = seek_answer_time
    elif question_type == constants.QUESTION_LINE_BY_CHORUS:
        start_index, index = get_chorus_question(lyrics)

        start_time = round(max(lyrics[start_index]["time"] - 0.8, 0), 2)
        end_time = round(lyrics[index]["time"] - 0.3, 2)
        end_answer_time = f',{round(lyrics[index + 1]["time"] - 0.1, 2)}' if index + 1 < len(lyrics) else ""
        seek_answer_time = round(lyrics[index - 1]["time"], 2)

        question["text"] = [line["text"] for line in lyrics[start_index:index]]
        question["answer"] = lyrics[index]["text"]
        question["question_timecode"] = f"{start_time},{end_time}"
        question["answer_timecode"] = f"{start_time}{end_answer_time}"
        question["answer_seek"] = seek_answer_time

    return question
