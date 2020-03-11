# Introduction
TODO: Give a short introduction of your project. Let this section explain the objectives or the motivation behind this project.

# Getting Started

Install [poetry](https://python-poetry.org/docs/).

Install required Ubuntu package:

```sh
apt install mssql-tools unixodbc unixodbc-dev
```

Install Python packages via `poetry`:

```sh
poetry install
```

# Running CommA

1. Enter the setup environment with `poetry shell`
2. Run `./CommA.py --upstream --downstream`

This will parse the upstream and downstream repos.
