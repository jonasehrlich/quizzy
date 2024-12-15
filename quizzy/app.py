from __future__ import annotations

import argparse
import pathlib

from textual import app, widgets

from quizzy import __version__, models


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=__name__.split(".")[0], description="A terminal quiz app")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("quizfile", type=pathlib.Path, help="Quiz file")
    return parser


class QuizzyApp(app.App[None]):
    def __init__(self, config: models.Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> app.ComposeResult:
        yield widgets.Header()
        yield widgets.Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"


def main() -> None:
    parser = get_arg_parser()
    namespace = parser.parse_args()

    config = models.load_config(namespace.quizfile)
    app = QuizzyApp(config)
    app.run()


if __name__ == "__main__":
    main()
