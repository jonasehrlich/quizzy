from __future__ import annotations

import argparse
import pathlib
import shlex
import sys
from typing import NoReturn

from textual import app, binding, containers, log, message, reactive, screen, widgets
from textual_serve import server

from quizzy import __version__, models

NoCorrectAnswerType = type("NoCorrectAnswerType", (object,), {})
NoCorrectAnswer = NoCorrectAnswerType()

QuestionScreenResult = models.Team | NoCorrectAnswerType | None


class AnswerScreen(screen.ModalScreen[QuestionScreenResult], can_focus=True):
    NOONE_ANSWERED_ID = "__noone-answered"

    BINDINGS = [
        binding.Binding("escape", "no_correct_answer", "Dismiss", key_display="Esc"),
    ]

    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        super().__init__(classes="question-answer-screen")
        self.category = category
        self.question = question
        self.teams = {team.id: team for team in teams}
        self.border_title = f"{category} - {question.value} points"

    def compose(self) -> app.ComposeResult:
        question_widget = widgets.Markdown(self.question.question, id="question")
        question_widget.border_title = "Question"

        answer_widget = widgets.Markdown(self.question.answer, id="answer")
        answer_widget.border_title = "Answer"

        who_answered = containers.HorizontalGroup(
            *[
                containers.Vertical(widgets.Button(team.name, id=team_id, variant="primary"))
                for team_id, team in self.teams.items()
            ],
            id="who-answered",
            classes="horizontal-100",
        )
        who_answered.border_title = "Who Answered Correctly?"

        container = containers.Grid(
            question_widget,
            answer_widget,
            who_answered,
            containers.Horizontal(
                widgets.Button(
                    "😭 No one answered correctly 😭", id=self.NOONE_ANSWERED_ID, variant="error", classes="button-100"
                ),
                classes="horizontal-100",
            ),
            classes="question-answer-dialog",
            id="dialog",
        )

        container.border_title = f"{self.category} - {self.question.value} points"
        yield widgets.Footer()
        yield container

    def action_no_correct_answer(self) -> None:
        self.dismiss(NoCorrectAnswer)

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == self.NOONE_ANSWERED_ID:
            self.dismiss(NoCorrectAnswer)
        elif event.button.id in self.teams:
            team = self.teams[event.button.id]
            self.dismiss(team)


class QuestionScreen(screen.ModalScreen[QuestionScreenResult], can_focus=True):
    SHOW_ANSWER_ID = "show-answer"
    BINDINGS = [
        binding.Binding("escape", "dismiss(None)", "Dismiss"),
    ]

    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        super().__init__(classes="question-answer-screen")
        self.category = category
        self.question = question
        self.teams = teams

    def compose(self) -> app.ComposeResult:
        question_widget = widgets.Markdown(self.question.question, id="question")
        question_widget.border_title = "Question"

        container = containers.Grid(
            question_widget,
            containers.Horizontal(
                widgets.Button("Show Answer", id=self.SHOW_ANSWER_ID, variant="primary", classes="button-100"),
                classes="horizontal-100",
            ),
            classes="question-answer-dialog",
            id="dialog",
        )

        container.border_title = f"{self.category} - {self.question.value} points"
        yield widgets.Footer()
        yield container

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        def dismiss(team: QuestionScreenResult) -> None:
            self.dismiss(team)

        if event.button.id == self.SHOW_ANSWER_ID:
            event.stop()
            self.app.push_screen(AnswerScreen(self.category, self.question, self.teams), dismiss)


class TeamScore(containers.Horizontal):
    MODIFIER_BUTTON_VALUE = 100
    _ADD_BUTTON_ID = f"add-{MODIFIER_BUTTON_VALUE}"
    _SUBTRACT_BUTTON_ID = f"subtract-{MODIFIER_BUTTON_VALUE}"
    score = reactive.reactive(0, recompose=True)

    def __init__(self, team: models.Team) -> None:
        self.team = team
        super().__init__()
        self.border_title = self.team.name
        self.score = team.score

    def compose(self) -> app.ComposeResult:
        yield widgets.Static(str(self.score))
        yield containers.Horizontal(
            widgets.Button("+ 100", id=self._ADD_BUTTON_ID, variant="success"),
            widgets.Button("- 100", id=self._SUBTRACT_BUTTON_ID, variant="error"),
            classes="modifier-buttons-container",
        )

    def on_button_pressed(self, event: widgets.Button.Pressed) -> None:
        if event.button.id == self._ADD_BUTTON_ID:
            self.score += self.MODIFIER_BUTTON_VALUE
            event.stop()
        elif event.button.id == self._SUBTRACT_BUTTON_ID:
            if self.score <= self.MODIFIER_BUTTON_VALUE:
                self.score = 0
            else:
                self.score -= self.MODIFIER_BUTTON_VALUE
            event.stop()

    def watch_score(self, score: int) -> None:
        """
        Watch the reactive score and update the team's score in the data object. This allows dumping the quiz state
        to YAML.
        """
        self.team.score = score


class Scoreboard(containers.Vertical):
    def __init__(self, teams: list[models.Team]) -> None:
        super().__init__()
        self.teams = teams
        self.team_score_widgets = {team.id: TeamScore(team) for team in teams}

    def compose(self) -> app.ComposeResult:
        yield containers.HorizontalGroup(*self.team_score_widgets.values())

    def update_team_score(self, team_id: str, value: int) -> None:
        log(f"scoreboard: Updating team score {team_id} to {value}")
        self.team_score_widgets[team_id].score += value


class QuestionButton(widgets.Button):
    class Answered(message.Message):
        def __init__(self, team: models.Team, question_value: int) -> None:
            self.team = team
            self.value = question_value
            super().__init__()

    def __init__(self, category: str, question: models.Question, teams: list[models.Team]) -> None:
        self.question = question
        self.teams = teams
        self.category = category
        super().__init__(str(question.value), variant="warning", classes="button-100")
        # Disable the button if the question has already been answered on init. This might be useful when starting with
        # a state
        self.disabled = question.answered

    def on_click(self) -> None:
        def wait_for_result(team: QuestionScreenResult) -> None:
            if team is None:
                return

            self.disabled = True
            self.question.answered = True
            if isinstance(team, NoCorrectAnswerType):
                log("question-button: No one answered the question")
            else:
                log(f"question-button: {team.id} answered the question")
                self.post_message(self.Answered(team, self.question.value))

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

    def __init__(self, config: models.Config) -> None:
        super().__init__()
        self.config = config
        self.scoreboard_widget = Scoreboard(self.config.teams)

    def compose(self) -> app.ComposeResult:
        yield widgets.Header()
        yield widgets.Footer()
        yield containers.Grid(QuestionBoard(self.config), self.scoreboard_widget, id="app-grid")

    def on_question_button_answered(self, event: QuestionButton.Answered) -> None:
        self.scoreboard_widget.update_team_score(event.team.id, event.value)

    def on_mount(self) -> None:
        self.theme = "textual-light"


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=__name__.split(".")[0],
        description="A quiz app to run in the terminal or the browser",
        epilog=(
            "When an unfinished quiz is closed, the state is saved to a timestamped quiz file in the current working "
            "directory."
        ),
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--dump-state-on-exit", action="store_true", help="Dump game state on exit")

    serve_group = parser.add_argument_group("Serve options")
    serve_group.add_argument("--serve", action="store_true", help="Serve the app through the browser")
    serve_group.add_argument("--host", default="localhost", help="Host to serve the app on")
    serve_group.add_argument("--port", type=int, default=8000, help="Port to serve the app on")

    parser.add_argument("quizfile", type=pathlib.Path, help="Quiz file")
    return parser


def serve_app(host: str, port: int) -> None:
    """Serve the app through textual-serve.

    :param host: Host to serve the app on
    :param port: Port to serve the app on
    """
    # The --serve flag is set, drop it from the args and serve the app instead through textual-serve
    args = list(sys.argv)
    args.remove("--serve")

    server.Server(shlex.join(args), host=host, port=port).serve()


def run_app(quiz_file: pathlib.Path, dump_state_on_exit: bool = False) -> None:
    """Run the app in the terminal.

    :param quizfile: File to use for this quiz
    """
    try:
        config = models.load_config(quiz_file)
    except Exception as e:
        print(f"Error loading quiz file: {e}", file=sys.stderr)
        sys.exit(1)
    app = QuizzyApp(config)
    try:
        app.run()
    finally:
        if dump_state_on_exit:
            models.dump_config_if_not_finished(config)


def main() -> NoReturn:
    parser = get_arg_parser()
    namespace = parser.parse_args()

    if namespace.serve:
        serve_app(namespace.host, namespace.port)
    else:
        run_app(namespace.quizfile, namespace.dump_state_on_exit)
    sys.exit(0)
