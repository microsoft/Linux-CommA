# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Plugin parent classes
"""

import logging
from typing import Set

import pluginlib


class Plugin:  # pylint: disable=too-few-public-methods
    """
    Base plugin class
    """

    schema = None

    def __init__(self, session, options):
        self.session = session
        self.config = session.config
        self.options = options
        # pylint: disable=no-member
        self.logger = logging.getLogger(f"plugins.{self.plugin_type}.{self.name}")


@pluginlib.Parent("paths")
class PathsPlugin(Plugin):
    """
    Parent class for path plugins
    These are used to dynamically determine which paths to monitor
    """

    @pluginlib.abstractmethod
    def get_paths(self) -> Set[str]:
        """
        Dynamically determine paths
        """
        raise NotImplementedError
