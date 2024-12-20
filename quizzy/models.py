from __future__ import annotations

import datetime
import json
import pathlib
from typing import Annotated, Any, Self

import pydantic
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


def is_multiple_of_100(v: int) -> int:
    if v % 100 != 0:
        raise ValueError("Value must be a multiple of 100")
    return v


@dataclass
class Question:
    question: str = Field(description="The question to ask. Markdown is supported.")
    answer: str = Field(description="The answer to the question. Markdown is supported.")
    value: Annotated[int, pydantic.AfterValidator(is_multiple_of_100)] = Field(
        gt=0, description="The value of the question in points. Must be a multiple of 100."
    )
    answered: bool = Field(default=False, description="Whether the question has been answered already.")

    def __str__(self) -> str:
        return self.question


@dataclass
class Category:
    name: str = Field(description="The name of the category.")
    questions: list[Question] = Field(max_length=5, description="The questions in this category.")

    @model_validator(mode="after")
    def sort_questions(self) -> Self:
        """Sort the questions in this category by their value."""

        self.questions.sort(key=lambda q: q.value)
        return self


@dataclass
class Config:
    categories: list[Category] = Field(max_length=5, description="The categories in the quiz.")
    teams: list[Team] = Field(default=[Team("Team 1"), Team("Team 2")], description="The teams in the quiz.")

    def is_finished(self) -> bool:
        for category in self.categories:
            for question in category.questions:
                if not question.answered:
                    return False
        return True


def _get_dict(path: pathlib.Path) -> dict[str, Any]:
    """Get the dictionary from a file.

    :param path: Path of the file to load.
    :raises ValueError: Raised if the file format is not supported.
    :return: Dictionary with the contents of the file.
    """
    with path.open() as f:
        if path.suffix == ".json":
            return json.load(f)
        if path.suffix in {".yml", ".yaml"}:
            return yaml.safe_load(f)
        raise ValueError(f"Unsupported file format: {path.suffix}")


def load_config(path: pathlib.Path) -> Config:
    raw = _get_dict(path)
    return Config(**raw)


def dump_config_if_not_finished(config: Config) -> None:
    """Dump the config if any of the questions is not answered yet.

    :param config: _description_
    """
    if config.is_finished():
        return
    p = pathlib.Path() / f"quizzy-run-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    print(f"This quiz is not finished yet. Saving current state to '{p}'.")
    print("This file can be re-used later.")
    with p.open("wb") as f:
        f.write(pydantic.TypeAdapter(Config).dump_json(config))
