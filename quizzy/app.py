from __future__ import annotations

import argparse
import pathlib

from textual import app, widgets, containers, screen, reactive
from quizzy import __version__, models


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=__name__.split(".")[0], description="A terminal quiz app")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("quizfile", type=pathlib.Path, help="Quiz file")
    return parser


class AnswerScreen(screen.ModalScreen[models.Team | None]):
    NOONE_ANSWERED_ID = "__noone-answered"

    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        super().__init__(classes="question-answer-screen")
        self.category = category
        self.question = question
        self.teams = {team.id(): team for team in teams}
        self.border_title = f"{category} - {question.value} points"

    def compose(self) -> app.ComposeResult:

        question_widget = widgets.Static(self.question.question, id="question")
        question_widget.border_title = "Question"

        answer_widget = widgets.Static(self.question.answer, id="answer")
        answer_widget.border_title = "Answer"

        whoanswered = containers.HorizontalGroup(
            *[containers.Vertical(widgets.Button(team.name, id=team_id, variant="success")) for team_id, team in self.teams.items()],
            id="who-answered", classes="horizontal-100",
        )
        whoanswered.border_title = "Who Answered Correctly?"

        container = containers.Grid(
            question_widget,
            answer_widget,
            whoanswered,
            containers.Horizontal(
                widgets.Button("😭 No one answered correctly 😭", id=self.NOONE_ANSWERED_ID, variant="error", classes="button-100"),
                classes="horizontal-100",
            ),
            classes="question-answer-dialog",
            id="dialog",
        )

        container.border_title = f"{self.category} - {self.question.value} points"
        yield container

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == self.NOONE_ANSWERED_ID:
            self.dismiss(None)
        elif event.button.id in self.teams:
            team = self.teams[event.button.id]
            self.dismiss(team)


class QuestionScreen(screen.ModalScreen[models.Team | None]):
    SHOW_ANSWER_ID = "show-answer"

    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        super().__init__(classes="question-answer-screen")
        self.category = category
        self.question = question
        self.teams = teams

    def compose(self) -> app.ComposeResult:
        question_widget = widgets.Static(self.question.question, id="question")
        question_widget.border_title = "Question"

        container = containers.Grid(
            question_widget,
            containers.Horizontal(
                widgets.Button("Show Answer", id=self.SHOW_ANSWER_ID, variant="primary", classes="button-100"), classes="horizontal-100"
            ),
            classes="question-answer-dialog",
            id="dialog",
        )

        container.border_title = f"{self.category} - {self.question.value} points"
        yield container

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:

        if event.button.id == self.SHOW_ANSWER_ID:
            self.app.push_screen(
                AnswerScreen(self.category, self.question, self.teams), lambda team_or_none: self.dismiss(team_or_none)
            )


class TeamScore(containers.Vertical):

    def __init__(self, team: models.Team) -> None:
        self.team = team
        super().__init__()
        self.border_title = self.team.name

    def compose(self) -> app.ComposeResult:
        score = widgets.Static(str(self.team.score))
        yield score


class Scoreboard(containers.HorizontalGroup):
    def __init__(self, teams: list[models.Team]) -> None:
        self.teams = teams
        super().__init__()

    def compose(self) -> app.ComposeResult:
        for team in self.teams:
            yield TeamScore(team)


class QuestionButton(widgets.Button):
    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        self.question = question
        self.teams = teams
        self.category = category
        super().__init__(str(question.value), variant="warning", classes="button-100")

    def on_click(self) -> None:
        # First, disable the button to prevent multiple clicks
        self.disabled = True

        def wait_for_result(team: models.Team | None) -> None:
            if team is not None:
                team.score += self.question.value

        self.app.push_screen(QuestionScreen(self.category, self.question, self.teams), wait_for_result)


class CategoryColumn(containers.VerticalGroup):
    def __init__(self, category: models.Category, teams: list[models.Team]) -> None:
        self.category = category
        self.teams = teams
        super().__init__()

    def compose(self) -> app.ComposeResult:
        yield widgets.Static(self.category.name)
        for question in self.category.questions:
            yield QuestionButton(self.category.name, question, self.teams)


class QuestionBoard(containers.HorizontalGroup):
    def __init__(self, config: models.Config) -> None:
        self.config = config
        super().__init__()

    def compose(self) -> app.ComposeResult:
        for category in self.config.categories:
            yield CategoryColumn(category, self.config.teams)


class QuizzyApp(app.App[None]):
    CSS_PATH = "quizzy.tcss"

    def __init__(self) -> None:
        super().__init__()
        parser = get_arg_parser()
        namespace = parser.parse_args()

        self.config = models.load_config(namespace.quizfile)

    def compose(self) -> app.ComposeResult:
        yield widgets.Header()
        yield widgets.Footer()
        yield containers.Grid(
            QuestionBoard(self.config), containers.Vertical(Scoreboard(self.config.teams)), id="app-grid"
        )
