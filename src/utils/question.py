import random
from typing import List, Set

from src import constants


def audio_to_question_types(audio: dict) -> Set[str]:
    question_types = {constants.QUESTION_ARTIST_BY_TRACK, constants.QUESTION_NAME_BY_TRACK}

    if "lyrics" in audio:
        question_types.add(constants.QUESTION_LINE_BY_TEXT)
        question_types.add(constants.QUESTION_LINE_BY_CHORUS)

        if audio["lyrics"][0]["time"] >= constants.INTRODUCTION_TIME:
            question_types.add(constants.QUESTION_ARTIST_BY_INTRO)

    return question_types


def get_question_type(questions: List[str], audio: dict) -> str:
    available_question_types = audio_to_question_types(audio)
    question_types = list(set(questions).intersection(available_question_types))
    return random.choice(question_types)


def make_question(audio: dict, question_type: str) -> dict:
    question = dict()
    artists = [artist["name"] for artist in audio["artists"]]
    lyrics = audio.get("lyrics", [])
    track_start = lyrics[0]["time"] if lyrics else ""

    if question_type == constants.QUESTION_ARTIST_BY_TRACK:
        question["answer"] = artists
        question["answer_string"] = ", ".join(artists)
        question["question_timecode"] = track_start
        question["answer_timecode"] = ""
    elif question_type == constants.QUESTION_ARTIST_BY_INTRO:
        question["answer"] = artists
        question["answer_string"] = ", ".join(artists)
        question["question_timecode"] = f'0,{round(lyrics[0]["time"] - 0.5, 2)}'
        question["answer_timecode"] = ""
    elif question_type == constants.QUESTION_NAME_BY_TRACK:
        question["answer"] = audio["track"]
        question["question_timecode"] = track_start
        question["answer_timecode"] = ""
    elif question_type == constants.QUESTION_LINE_BY_TEXT or question_type == constants.QUESTION_LINE_BY_CHORUS:
        # TODO: make correct for chorus
        index = random.randint(3, len(lyrics) - 2)
        start_time = round(lyrics[index - 3]["time"] - 0.8, 2)
        end_time = round(lyrics[index]["time"] - 0.3, 2)
        end_answer_time = round(lyrics[index + 1]["time"] - 0.1, 2)

        question["text"] = [line["text"] for line in lyrics[index - 3:index]]
        question["answer"] = lyrics[index]["text"]
        question["question_timecode"] = f"{start_time},{end_time}"
        question["answer_timecode"] = f"{start_time},{end_answer_time}"

    return question