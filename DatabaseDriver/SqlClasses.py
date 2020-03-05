from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

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


class PatchDataMeta(Base):
    __tablename__ = "PatchDataMeta"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    priority = Column(Integer)


class Distros(Base):
    __tablename__ = "Distros"
    distroID = Column(String, primary_key=True)
    repoLink = Column(String)


class MonitoringSubjects(Base):
    __tablename__ = "MonitoringSubjects"
    monitoringSubjectID = Column(Integer, primary_key=True)
    distroID = Column(String, ForeignKey("Distros.distroID"))
    revision = Column(String)


class MonitoringSubjectsMissingPatches(Base):
    __tablename__ = "MonitoringSubjectsMissingPatches"
    monitoringSubjectID = Column(
        Integer, ForeignKey("MonitoringSubjects.monitoringSubjectID"), primary_key=True
    )
    patchID = Column(Integer, ForeignKey("PatchData.patchID"))


class UpstreamPatchStatuses(Base):
    __tablename__ = "UpstreamPatchStatuses"
    patchID = Column(Integer, ForeignKey("PatchData.patchID"), primary_key=True)
    status = Column(String)


engine = create_engine("sqlite:///:memory:", echo=True)
