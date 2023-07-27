# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Configuration data model
"""

from typing import Any, Dict, Optional, Sequence, Tuple, Union

from pluginlib import PluginlibError, PluginLoader
from pydantic import AnyUrl, BaseModel, root_validator, validator

import comma.plugins  # pylint: disable=unused-import  # Loads parent classes  # noqa: F401
from comma.util import DateString


class Target(BaseModel):
    """
    Target is a repo and reference pair
    """

    repo: str
    reference: str  # TODO (Issue 28): This should pull from plugins


class Upstream(BaseModel):
    """
    Model for upstream definition
    """

    paths: Tuple[Union[str, Dict[str, Any]], ...]
    reference: str = "HEAD"
    repo: str

    @validator("paths")
    def check_paths(cls, value: str):
        """Coerce date string"""

        seen = []
        for path in value:
            if path in seen:
                raise ValueError(f"Duplicate entries for path '{path}'")

            if isinstance(path, dict):
                if len(path) > 1:
                    raise ValueError(
                        f"Multiple keys specified for dictionary: {value}\nAre plugin options indented under plugin name?"
                    )

                plugin_name = next(iter(path))
                if not plugin_name.startswith("^"):
                    raise ValueError(f"Plugin name '{plugin_name}' does not start with '^'")

            seen.append(path)

        return value


class Spreadsheet(BaseModel):
    """
    Model for spreadsheet configuration
    """

    excluded_paths: Optional[Tuple[str, ...]]


class BasicConfig(BaseModel):
    """
    Minimal configuration model
    """

    downstream_since: Optional[DateString] = None
    upstream_since: Optional[DateString] = None
    plugin_modules: Optional[Sequence[str]] = ["comma.plugins.paths"]
    plugin_paths: Optional[Sequence[str]] = None
    plugins: Optional[Dict[str, Any]] = None

    @validator("downstream_since", "upstream_since")
    def coerce_date(cls, value: str):
        """Coerce date string"""

        return value if value is None else DateString(value)

    @root_validator
    def load_plugins(cls, values):
        """Load plugins"""

        try:
            values["plugins"] = PluginLoader(
                modules=values["plugin_modules"], paths=values["plugin_paths"]
            ).plugins
        except PluginlibError as e:
            raise ValueError(f"Unable to load plugins: {e}") from e

        return values

    class Config:
        """Model configuration"""

        validate_assignment = True


class FullConfig(BasicConfig):
    """
    Full configuration model
    Requires:
        upstream to be defined
    """

    repos: Dict[str, AnyUrl]
    upstream: Upstream
    downstream: Optional[Tuple[Target, ...]] = ()
    spreadsheet: Optional[Spreadsheet] = Spreadsheet()

    @validator("repos")
    def check_repo(cls, repos):
        """Validate repository definitions"""

        for key, value in repos.items():
            if not key:
                raise ValueError(f"No name provided for repo at {value}")
            if " " in key:
                raise ValueError(f"Repo names can not contain spaces: '{key}'")

        return repos

    @validator("upstream")
    def check_upstream(cls, value: Upstream, values):
        """Validate upstream definition"""

        if value.repo not in values["repos"]:
            raise ValueError(f"Undefined repo '{value.repo}' defined for upstream")

        return value

    @validator("downstream", each_item=True)
    def check_downstream(cls, value: Target, values):
        """Validate downstream target definitions"""
        if value.repo not in values["repos"]:
            raise ValueError(f"Undefined repo '{value.repo}' defined for downstream")

        return value
