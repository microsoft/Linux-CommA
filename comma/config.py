# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Configuration data model
"""

from typing import Dict, Optional, Tuple

from pydantic import AnyUrl, BaseModel, validator

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

    paths: Tuple[str, ...]  # TODO (Issue 28): This should pull from plugins
    reference: str = "HEAD"
    repo: str
    sections: Tuple[str, ...]


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

    @validator("downstream_since", "upstream_since")
    def coerce_date(cls, value: str):
        """Coerce date string"""

        return value if value is None else DateString(value)

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
    downstream: Optional[Tuple[Target, ...]]
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
