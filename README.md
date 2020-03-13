# Introduction
This tool populates a database with the details of which patches that are
upstream (in `linux-mainline`) are missing from distros in their downstream
kernels (e.g. Ubuntu kernels). For our use case, we are looking at Hyper-V
patches and checking downstream azure specific kernels, but this is adaptable.

## Getting Started

Install [poetry](https://python-poetry.org/docs/).

Install required Ubuntu package:

```sh
apt install mssql-tools unixodbc unixodbc-dev
```

Install Python packages via `poetry`:

```sh
poetry install
```

## Running CommA

1. Enter the setup environment with `poetry shell`
2. Run `./CommA.py --upstream --downstream`

This will parse the upstream and downstream repos.
