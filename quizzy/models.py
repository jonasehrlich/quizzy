from __future__ import annotations

import pathlib
from typing import Self

import yaml
from pydantic import Field, model_validator
from pydantic.dataclasses import dataclass


@dataclass
class Team:
    name: str = Field(min_length=2)
    score: int = Field(default=0, ge=0)
    id: str = Field(init=False)

    def __post_init__(self) -> None:
        self.id = self.name.replace(" ", "-").lower()

    def __str__(self) -> str:
        return self.name


@dataclass
class Question:
    question: str
    answer: str
    value: int = Field(gt=0)
    answered: bool = False

    def __str__(self) -> str:
        return self.question


@dataclass
class Category:
    name: str
    questions: list[Question] = Field(max_length=5)

    @model_validator(mode="after")
    def sort_questions(self) -> Self:
        """Sort the questions in this category by their value."""

        self.questions.sort(key=lambda q: q.value)
        return self


@dataclass
class Config:
    categories: list[Category] = Field(max_length=5)
    teams: list[Team] = Field(default=[Team("Team 1"), Team("Team 2")])
    # TODO: Support random questions


def load_config(path: pathlib.Path) -> Config:
    with path.open() as f:
        raw = yaml.safe_load(f)

    return Config(**raw)
