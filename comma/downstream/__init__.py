# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Operations for downstream targets
"""

import logging
import sys

from comma.database.driver import DatabaseDriver
from comma.database.model import Distros, MonitoringSubjects


LOGGER = logging.getLogger(__name__.split(".", 1)[0])


def list_downstream():
    """List downstream targets"""

    with DatabaseDriver.get_session() as session:
        for distro, revision in (
            session.query(Distros.distroID, MonitoringSubjects.revision)
            .outerjoin(MonitoringSubjects, Distros.distroID == MonitoringSubjects.distroID)
            .all()
        ):
            print(f"{distro}\t{revision}")


def add_downstream_target(options):
    """
    Add a downstream target
    """

    with DatabaseDriver.get_session() as session:
        # Add repo
        if options.url:
            session.add(Distros(distroID=options.name, repoLink=options.url))
            LOGGER.info("Successfully added new repo %s at %s", options.name, options.url)

        # If URL wasn't given, make sure repo is in database
        elif (options.name,) not in session.query(Distros.distroID).all():
            sys.exit(f"Repository '{options.name}' given without URL not found in database")

        # Add target
        session.add(MonitoringSubjects(distroID=options.name, revision=options.revision))
        LOGGER.info(
            "Successfully added new revision '%s' for distro '%s'", options.revision, options.name
        )
