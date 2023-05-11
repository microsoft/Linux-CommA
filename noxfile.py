# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Nox configuration file
See https://nox.thea.codes/en/stable/config.html
"""

import platform
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import nox
import toml

CURRENT_PYTHON = sys.executable or f"{sys.version_info.major}.{sys.version_info.minor}"
ON_WINDOWS = platform.system() == "Windows"

CONFIG = toml.load("pyproject.toml")
DEPENDENCIES = CONFIG["project"]["dependencies"]
OPTIONAL_DEPENDENCIES = CONFIG["project"]["optional-dependencies"]
NOX_DEPENDENCIES = ("nox", "toml")


# Global options
nox.options.stop_on_first_error = False
nox.options.error_on_missing_interpreters = False

# Require support for tags
nox.needs_version = ">=2022.8.7"


# --- Formatting ---


@nox.session(python=CURRENT_PYTHON, tags=["format", "all"])
def black(session: nox.Session) -> None:
    """Run black"""
    session.install(*OPTIONAL_DEPENDENCIES["black"], silent=False)
    session.run("black", ".")


@nox.session(python=CURRENT_PYTHON, tags=["format", "all"])
def isort(session: nox.Session) -> None:
    """Run isort"""
    session.install(*OPTIONAL_DEPENDENCIES["isort"], silent=False)
    session.run("isort", ".")


# --- Linting ---


@nox.session(python=CURRENT_PYTHON, tags=["lint", "all"])
def flake8(session: nox.Session) -> None:
    """Run flake8"""
    session.install(
        *OPTIONAL_DEPENDENCIES["black"],
        *OPTIONAL_DEPENDENCIES["flake8"],
        *OPTIONAL_DEPENDENCIES["isort"],
        silent=False,
    )
    session.run("flake8")


@nox.session(python=CURRENT_PYTHON, tags=["lint", "all"])
def pylint(session: nox.Session) -> None:
    """Run pylint"""
    session.install(
        *OPTIONAL_DEPENDENCIES["pylint"], *DEPENDENCIES, *NOX_DEPENDENCIES, silent=False
    )
    session.run("pylint", "comma", "*.py")


# --- Functional tests ---


@nox.session(python=CURRENT_PYTHON)
def demo(session: nox.Session) -> None:
    """Functional test"""
    session.install(".", silent=False)

    # Remove existing sqlite datebase to avoid unique key error
    Path("comma.db").unlink(missing_ok=True)

    session.run(
        "comma",
        "--dry-run",
        "--since",
        "6 months ago",
        "--verbose",
        "add-distro",
        "--name",
        "Ubuntu22.04",
        "--url",
        "https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/jammy",
        "--revision",
        "Ubuntu-azure-6.2-6.2.0-1004.4_22.04.1",
        silent=False,
    )

    session.run(
        "comma",
        "--dry-run",
        "--since",
        "6 months ago",
        "--verbose",
        "run",
        "--upstream",
        "--downstream",
        silent=False,
    )


@nox.session(python=CURRENT_PYTHON)
def symbols(session: nox.Session) -> None:
    """Print missing symbols"""
    session.install(".", silent=False)
    temp_file = NamedTemporaryFile(delete=False, prefix="CommA_")
    try:
        session.run(
            "comma",
            "--dry-run",
            "--no-fetch",
            "--verbose",
            "print-symbols",
            "--file",
            temp_file.name,
        )
    finally:
        Path(temp_file.name).unlink()


# --- Utility ---


@nox.session(python=CURRENT_PYTHON)
def run(session: nox.Session) -> None:
    """Install and run in a virtual environment"""
    session.install(".", silent=False)
    session.run("comma", *session.posargs)


@nox.session(python=CURRENT_PYTHON)
def dev(session: nox.Session) -> None:
    """
    Create virtual environment for development
    """

    # Determine paths
    venv_path = ".venv"

    if ON_WINDOWS:
        venv_python = str(Path(venv_path).resolve() / "Scripts" / "python.exe")
    else:
        venv_python = str(Path(venv_path).resolve() / "bin" / "python")

    # Install virtualenv, it's used to create the final virtual environment
    session.install("virtualenv", silent=False)

    # Create virtual environment
    session.run("virtualenv", "--python", str(session.python), "--prompt", "comma", venv_path)

    # Make sure pip and setuptools are up-to-date
    session.run(
        venv_python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "setuptools",
        external=True,
    )

    # Editable install
    session.run(
        venv_python,
        "-m",
        "pip",
        "install",
        "--editable",
        ".",
        external=True,
    )

    # Install dev tools
    session.run(
        venv_python,
        "-m",
        "pip",
        "install",
        *OPTIONAL_DEPENDENCIES["black"],
        *OPTIONAL_DEPENDENCIES["flake8"],
        *OPTIONAL_DEPENDENCIES["isort"],
        *OPTIONAL_DEPENDENCIES["pylint"],
        *NOX_DEPENDENCIES,
        external=True,
    )

    # Instruct user how to activate environment
    print("\nVirtual environment installed\nTo activate:\n")
    if ON_WINDOWS:
        print(
            f"   {venv_path}\\Scripts\\activate.bat\n"
            "       OR\n"
            f"   {venv_path}\\Scripts\\activate.ps1\n"
        )

    else:
        print(f"    source {venv_path}/bin/activate\n")
