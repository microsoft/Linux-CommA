# Introduction
This tool populates a database with the details of which patches that are
upstream (in `linux-mainline`) are missing from distros in their downstream
kernels (e.g. Ubuntu kernels). For our use case, we are looking at Hyper-V
patches and checking downstream azure specific kernels, but this is adaptable.

## Getting Started

Install `python3` via `apt` and then it as default:

> This is not technically required but is a recommended configuration, as
> `poetry` expects _some_ Python at `python`. You could also install Python 2.7.

```bash
apt install python3 python3-pip python3-venv
update-alternatives --install /usr/bin/python python /usr/bin/python3 1
update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
```

Install [poetry](https://python-poetry.org/docs/):

> Caution: this modifies your `.bashrc`.

```sh
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```

Setup [Microsoft SQL
repos](https://docs.microsoft.com/en-us/sql/linux/quickstart-install-connect-ubuntu?view=sql-server-ver15#tools)
(this is for `mssql-tools`):

> Caution: these commands use `sudo` and add a package repository. Change the
> Ubuntu version to your version (`cat /etc/os-release` for the number).

```sh
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/18.04/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
```

Install the required packages for connecting to the Microsoft SQL database:

```sh
apt update
apt install mssql-tools unixodbc-dev
```

Install Python packages via `poetry`:

```sh
poetry install
```

For the symbol matcher, install `exuberant-ctags` as the default `ctags` will
not work:

```sh
apt install exuberant-ctags
```

## Running CommA

1. Enter the setup environment with `poetry shell`
2. Provide the URL to the secrets repo with `export
   COMMA_SECRETS_URL=<URL/to/secrets/repo>`.
3. Run `./CommA.py run --upstream --downstream`

This will parse the upstream and downstream repos.

## Setting Up Secrets

You should have a separate Git repository which contains an XML file with your
database secrets, structured like:

```xml
</secrets><?xml version="1.0"?>
<secrets>
    <DatabaseServer>your.database.server.url</DatabaseServer>
    <DatabaseName>your_database_name</DatabaseName>
    <DatabaseUser>your_database_user</DatabaseUser>
    <DatabasePassword>your_database_password</DatabasePassword>
</secrets>
```

The file should be named `PatchTrackerSecrets.xml` and exist at the root level.
