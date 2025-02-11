# Quizzy

A quiz app using [textual](https://textual.textualize.io/).

![Question board](assets/game.gif)

## Configuration and Questions

Create a YAML file to define the teams participating, the questions and their answers.

```yaml
teams:
  - name: "Team 1"
  - name: "Team 2"
categories:
  - name: "General Knowledge"
    questions:
      - question: "What is the capital of France?"
        answer: "Paris"
        value: 100
      - question: "What is the capital of Germany?"
        answer: "Berlin"
        value: 200
  - name: "Science"
    questions:
      - question: "What is the chemical symbol for gold?"
        answer: "Au"
        value: 100
      - question: "What is the chemical symbol for silver?"
        answer: "Ag"
        value: 200
```

See [examples/quizzy.yaml](examples/quizzy.yaml) for an example.

## Running it

Run the latest PyPI release using *uvx*:

```sh
uvx quizzy projects/gh/quizzy/examples/quizzy.yaml
```

Run the local version using *uv*:

``` sh
uv run quizzy examples/quizzy.yaml
```

Serve on a webserver using textual:

``` sh
uvx quizzy --serve examples/quizzy.yaml
```

Run in development mode:

``` sh
uv run textual run --dev quizzy.app:QuizzyApp examples/quizzy.yaml
```
