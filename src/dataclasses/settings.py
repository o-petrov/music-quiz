from dataclasses import dataclass
from datetime import datetime
from typing import List

from src import constants


@dataclass
class Settings:
    theme: str
    start_year: int
    end_year: int
    questions: List[str]
    question_artists: List[str]
    text_languages: List[str]

    @classmethod
    def from_dict(cls: "Settings", data: dict) -> "Settings":
        theme = data.get("theme", "light")
        start_year = data.get("start_year", 1900)
        end_year = data.get("end_year", datetime.today().year)
        questions = data.get("questions", constants.QUESTIONS)
        question_artists = data.get("question_artists", constants.QUESTION_ARTISTS)
        text_languages = data.get("text_languages", constants.TEXT_LANGUAGES)
        return cls(theme, start_year, end_year, questions, question_artists, text_languages)

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "questions": self.questions,
            "question_artists": self.question_artists,
            "text_languages": self.text_languages
        }

    def to_query(self) -> dict:
        query = {
            "year": {"$gte": self.start_year, "$lte": self.end_year},
            "$or": [self.__question_to_query(question_type) for question_type in self.questions],
            **self.__question_artists_to_query()
        }

        return query

    def __question_to_query(self, question_type: str) -> dict:
        if question_type == constants.QUESTION_ARTIST_BY_TRACK:
            return {}

        if question_type == constants.QUESTION_ARTIST_BY_INTRO:
            return {"lyrics": {"$exists": True, "$ne": []}, "lyrics.0.time": {"$gte": constants.INTRODUCTION_TIME}}

        if question_type == constants.QUESTION_NAME_BY_TRACK:
            return {}

        if question_type == constants.QUESTION_LINE_BY_TEXT:
            return {"lyrics": {"$exists": True, "$ne": []}, "creation": {"$in": self.text_languages}}

        if question_type == constants.QUESTION_LINE_BY_CHORUS:
            return {"lyrics": {"$exists": True, "$ne": []}, "creation": {"$in": self.text_languages}}

        raise ValueError(f'Invalid question_type "{question_type}"')

    def __question_artists_to_query(self) -> dict:
        if self.question_artists == constants.QUESTION_ARTISTS:
            return {}

        if self.question_artists == [constants.QUESTION_ARTISTS_SOLE]:
            return {"artists": {"$size": 1}}

        if self.question_artists == [constants.QUESTION_ARTISTS_FEATS]:
            return {"artists.1": {"$exists": True}}

        raise ValueError(f'Invalid question_artists "{self.question_artists}"')
