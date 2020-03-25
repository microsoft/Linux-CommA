from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PatchData(Base):
    __tablename__ = "PatchData"
    patchID = Column(Integer, primary_key=True)
    subject = Column(String)
    commitID = Column(String)
    description = Column(String)
    author = Column(String)
    authorEmail = Column(String)
    authorTime = Column(DateTime())
    # TODO: What about committer and their email?
    commitTime = Column(DateTime())
    # TODO: Should we have a filenames table?
    affectedFilenames = Column(String)
    commitDiffs = Column(String)
    # TODO: Should we have a symbols table?
    symbols = Column(String)
    # TODO: Should this reference a patchID?
    fixedPatches = Column(String)
    # TODO: If this 1-1, why isn't `priority` just a column on `PatchData`?
    metaData = relationship("PatchDataMeta", uselist=False, back_populates="patch")
    # TODO: If this 1-1, why isn't `status` just a column on `PatchData`?
    upstreamStatus = relationship(
        "UpstreamPatchStatuses", uselist=False, back_populates="patch"
    )
    monitoringSubject = relationship(
        "MonitoringSubjectsMissingPatches", back_populates="patches"
    )


class PatchDataMeta(Base):
    __tablename__ = "PatchDataMeta"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    priority = Column(Integer)
    patch = relationship("PatchData", uselist=False, back_populates="metaData")


class UpstreamPatchStatuses(Base):
    __tablename__ = "UpstreamPatchStatuses"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    status = Column(String)
    patch = relationship("PatchData", uselist=False, back_populates="upstreamStatus")


class Distros(Base):
    # TODO: Rename this class and table to "Distro"
    __tablename__ = "Distros"
    distroID = Column(String, primary_key=True)
    repoLink = Column(String)
    monitoringSubject = relationship("MonitoringSubjects", back_populates="distro")


class MonitoringSubjects(Base):
    __tablename__ = "MonitoringSubjects"
    monitoringSubjectID = Column(Integer, primary_key=True)
    distroID = Column(String, ForeignKey("Distros.distroID"))
    revision = Column(String)
    distro = relationship("Distros", back_populates="monitoringSubject")
    missingPatch = relationship(
        "MonitoringSubjectsMissingPatches", back_populates="monitoringSubject"
    )


class MonitoringSubjectsMissingPatches(Base):
    __tablename__ = "MonitoringSubjectsMissingPatches"
    monitoringSubjectID = Column(
        Integer, ForeignKey("MonitoringSubjects.monitoringSubjectID"), primary_key=True
    )
    monitoringSubject = relationship(
        "MonitoringSubjects", back_populates="missingPatch"
    )
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    patches = relationship("PatchData", back_populates="monitoringSubject")
