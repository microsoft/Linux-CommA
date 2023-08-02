# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Plugin for Linux kernel maintainers file
"""

import re
from typing import Iterable, Set

from comma.plugins import PathsPlugin


UPSTREAM_TAG = re.compile(r"v\d+\.\d+.+$")


def extract_paths(sections: Iterable, content: str) -> Set[str]:
    # pylint: disable=wrong-spelling-in-docstring
    """
    Get set of files under the given sections.

    The MAINTAINERS file sections look like:

    Hyper-V CORE AND DRIVERS
    M:	"K. Y. Srinivasan" <kys@microsoft.com>
    ...
    F:	Documentation/ABI/stable/sysfs-bus-vmbus
    F:	arch/x86/hyperv
    F:	drivers/clocksource/hyperv_timer.c
    F:	drivers/hv/
    ...
    F:	tools/hv/

    Each section ends with a blank line.
    """

    remaining = set(sections)
    in_section = False
    paths = set()
    for line in content.splitlines():
        if in_section:
            # Section ends with a blank line
            if not line.strip():
                in_section = False

                # If there are no more sections, end now
                if not remaining:
                    break

            # Extract Paths
            if line.startswith("F:"):
                path = line.strip().split(maxsplit=1)[-1]

                # Skip Documentation
                if not path.startswith("Documentation"):
                    paths.add(path)

        # Look for start of a section
        elif current := next((section for section in remaining if section in line), None):
            in_section = True
            remaining.remove(current)

    return paths


class Maintainers(PathsPlugin):
    """
    Plugin for dynamically determining paths from Linux MAINTAINERS file
    """

    _alias_ = "linux_maintainers"

    def get_paths(self) -> Set[str]:
        repo = self.session.repo

        self.logger.debug("Parsing MAINTAINERS file for %s", repo.name)

        # Start with paths from the default reference
        sections = self.options["sections"]
        paths = set(
            extract_paths(sections, repo.git.show(f"origin/{repo.default_ref}:MAINTAINERS"))
        )

        # I
        for tag in repo.tags:
            # Only look at upstream tags newer than since date
            if not UPSTREAM_TAG.match(tag.name):
                continue
            if (
                self.config.upstream_since
                and tag.commit.committed_datetime < self.config.upstream_since.datetime
            ):
                continue

            paths |= extract_paths(sections, repo.git.show(f"{tag}:MAINTAINERS"))

        self.logger.debug("Completed parsing MAINTAINERS file for %s", repo.name)

        return paths
