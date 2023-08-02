# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Configuration data model
"""

from functools import cached_property
from typing import Any, Dict, Optional, Sequence, Tuple, Union

from pluginlib import PluginlibError, PluginLoader
from pydantic import AnyUrl, BaseModel, ConfigDict, computed_field, field_validator, model_validator

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

    @field_validator("paths")
    @classmethod
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

    excluded_paths: Optional[Tuple[str, ...]] = None


class BasicConfig(BaseModel):
    """
    Minimal configuration model
    """

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    downstream_since: Optional[Union[str, DateString]] = None
    upstream_since: Optional[Union[str, DateString]] = None
    plugin_modules: Optional[Sequence[str]] = ["comma.plugins.paths"]
    plugin_paths: Optional[Sequence[str]] = None

    @field_validator("downstream_since", "upstream_since")
    @classmethod
    def coerce_date(cls, value: str):
        """Coerce date string"""

        return value if value is None else DateString(value)

    @computed_field
    @cached_property
    def plugins(self) -> dict:
        """Cached plugins"""

        try:
            return PluginLoader(modules=self.plugin_modules, paths=self.plugin_paths).plugins
        except PluginlibError as e:
            raise ValueError(f"Unable to load plugins: {e}") from e

    @model_validator(mode="after")
    def load_plugins(self):
        """Load plugins during validation to catch errors"""

        self.plugins  # pylint: disable=pointless-statement

        return self


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

    @field_validator("repos")
    @classmethod
    def check_repo(cls, repos):
        """Validate repository definitions"""

        for key, value in repos.items():
            if not key:
                raise ValueError(f"No name provided for repo at {value}")
            if " " in key:
                raise ValueError(f"Repo names can not contain spaces: '{key}'")

        return repos

    @model_validator(mode="after")
    def check_upstream(self) -> Any:
        """Validate upstream definition"""

        if self.upstream.repo not in self.repos:
            raise ValueError(f"Undefined repo '{self.upstream.repo}' defined for upstream")

        return self

    @model_validator(mode="after")
    def check_downstream(self) -> Any:
        """Validate downstream target definitions"""

        for target in self.downstream:
            if target.repo not in self.repos:
                raise ValueError(f"Undefined repo '{target.repo}' defined for downstream")

        return self
