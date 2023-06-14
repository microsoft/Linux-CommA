# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
ORM models for database objects
"""

from datetime import datetime

import git
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from comma.util import format_diffs
from comma.util.tracking import get_filenames


IGNORED_IN_CMSG = "reported-by:", "signed-off-by:", "reviewed-by:", "acked-by:", "cc:"

Base = declarative_base()

# pylint: disable=invalid-name,too-few-public-methods


class PatchData(Base):
    """
    Data and metadata for a patch/commit
    """

    __tablename__ = "PatchData"
    patchID = Column(Integer, primary_key=True)
    subject = Column(String)
    commitID = Column(String)
    description = Column(String)
    author = Column(String)
    authorEmail = Column(String)
    authorTime = Column(DateTime())
    # TODO (Issue 40): What about committer and their email?
    commitTime = Column(DateTime())
    # TODO (Issue 40): Should we have a filenames table?
    affectedFilenames = Column(String)
    commitDiffs = Column(String)
    # TODO (Issue 40): Should we have a symbols table?
    symbols = Column(String)
    # TODO (Issue 40): Should this reference a patchID?
    fixedPatches = Column(String)
    # TODO (Issue 40): If this 1-1, why isn't `priority` just a column on `PatchData`?
    metaData = relationship("PatchDataMeta", uselist=False, back_populates="patch")
    # TODO (Issue 40): If this 1-1, why isn't `status` just a column on `PatchData`?
    upstreamStatus = relationship("UpstreamPatchStatuses", uselist=False, back_populates="patch")
    monitoringSubject = relationship(
        "MonitoringSubjectsMissingPatches",
        back_populates="patches",
        lazy="dynamic",
    )

    @classmethod
    def create(cls, commit: git.Commit, paths) -> "PatchData":
        """
        Create patch object from a commit object
        """

        patch = cls(
            commitID=commit.hexsha,
            author=commit.author.name,
            authorEmail=commit.author.email,
            authorTime=datetime.utcfromtimestamp(commit.authored_date),
            commitTime=datetime.utcfromtimestamp(commit.committed_date),
        )

        description = []
        fixed_patches = []
        for num, line in enumerate(commit.message.splitlines()):
            line = line.strip()  # pylint: disable=redefined-loop-name
            if not num:
                patch.subject = line
                continue

            if line.lower().startswith(IGNORED_IN_CMSG):
                continue

            description.append(line)

            # Check if this patch fixes other patches
            if line.lower().startswith("fixes:"):
                words = line.split(" ")
                if len(words) > 1:
                    fixed_patches.append(words[1])

        patch.description = "\n".join(description)
        patch.fixedPatches = " ".join(fixed_patches)  # e.g. "SHA1 SHA2 SHA3"
        patch.affectedFilenames = " ".join(get_filenames(commit))
        patch.commitDiffs = format_diffs(commit, paths)

        return patch


class PatchDataMeta(Base):
    """
    Holds the priority for a patch
    """

    __tablename__ = "PatchDataMeta"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    priority = Column(Integer)
    patch = relationship("PatchData", uselist=False, back_populates="metaData")


class UpstreamPatchStatuses(Base):
    """
    Holds the status for a patch
    """

    __tablename__ = "UpstreamPatchStatuses"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    status = Column(String)
    patch = relationship("PatchData", uselist=False, back_populates="upstreamStatus")


class Distros(Base):
    """
    Downstream distro and URL for downstream repo
    """

    # TODO (Issue 40): Rename this class and table to "Distro"
    __tablename__ = "Distros"
    distroID = Column(String, primary_key=True)
    repoLink = Column(String)
    monitoringSubject = relationship("MonitoringSubjects", back_populates="distro")


class MonitoringSubjects(Base):
    """
    Reference and distro pair to monitor
    """

    __tablename__ = "MonitoringSubjects"
    monitoringSubjectID = Column(Integer, primary_key=True)
    distroID = Column(String, ForeignKey("Distros.distroID"))
    revision = Column(String)
    distro = relationship("Distros", back_populates="monitoringSubject")
    missingPatches = relationship(
        "MonitoringSubjectsMissingPatches",
        back_populates="monitoringSubject",
        lazy="dynamic",
    )


class MonitoringSubjectsMissingPatches(Base):
    """
    Patches missing for a given monitoring subject
    """

    # TODO (Issue 40): Rename this table.
    __tablename__ = "MonitoringSubjectsMissingPatches"
    monitoringSubjectID = Column(
        Integer, ForeignKey("MonitoringSubjects.monitoringSubjectID"), primary_key=True
    )
    monitoringSubject = relationship(
        "MonitoringSubjects",
        back_populates="missingPatches",
        single_parent=True,
        # This ensures that when we delete a parent monitoring subject
        # (as referenced by the foreign key above), that this is deleted too.
        cascade="all, delete-orphan",
    )
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    patches = relationship("PatchData", back_populates="monitoringSubject")
