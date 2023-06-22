# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions and classes for fetching and parsing data from Git
"""

import logging
import pathlib
import re
from typing import Any, Iterable, List, Optional, Set, Tuple

import approxidate
import git


LOGGER = logging.getLogger(__name__)


def get_filenames(commit: git.Commit) -> List[str]:
    """
    Get all paths affected by a given commit
    """

    if commit.parents:
        return []
    diffs = commit.tree.diff(commit.parents[0])
    # Sometimes a path is in A and not B but we want all filenames.
    return list(
        {diff.a_path for diff in diffs if diff.a_path is not None}
        | {diff.b_path for diff in diffs if diff.b_path is not None}
    )


class Repo:
    """
    Common repository operations
    Wraps git.Repo, so unimplemented methods are passed to self.obj
    """

    def __init__(self, name: str, url: str, default_ref: str = "HEAD") -> None:
        self.name: str = name
        self.url: str = url
        self.path = path = pathlib.Path("Repos", name).resolve()
        self.obj: Optional[git.Repo] = git.Repo(path) if path.exists() else None
        self._tracked_paths: Optional[tuple] = None
        self.default_ref = default_ref

    def __getattr__(self, name: str) -> Any:
        return getattr(self.obj, name)

    def fetch(self, since: Optional[str] = None, ref: Optional[str] = None, repack: bool = False):
        """Fetch repo"""

        if repack:
            LOGGER.info("Repacking '%s' repo", self.name)
            self.obj.git.repack("-d")

        if since:
            LOGGER.info("Fetching '%s' repo since %s", self.name, since)
            kwargs = {"shallow_since": since}
        else:
            LOGGER.info("Fetching '%s' repo", self.name)
            kwargs = {}

        try:
            self.obj.remotes.origin.fetch(
                ref or self.default_ref, verbose=True, progress=GitProgressPrinter(), **kwargs
            )
            LOGGER.info("Completed fetching %s", self.name)
        except git.GitCommandError as e:
            # Sometimes a shallow-fetched repo will need repacking before fetching again
            if "fatal: error in object: unshallow" in e.stderr and not repack:
                LOGGER.warning("Error with shallow clone. Repacking before retrying.")
                self.fetch(repack=True)
            else:
                raise

    def clone(self, since: Optional[str] = None):
        """Clone repo"""

        if since:
            LOGGER.info("Cloning '%s' repo from '%s' shallow since %s", self.name, self.url, since)
            args = {"shallow_since": since}
        else:
            LOGGER.info("Cloning '%s' repo from '%s'.", self.name, self.url)
            args = {}

        self.obj = git.Repo.clone_from(self.url, self.path, **args, progress=GitProgressPrinter())
        LOGGER.info("Completed cloning %s", self.name)

    def pull(self, ref: Optional[str] = None):
        """Pull repo"""
        LOGGER.info("Pulling '%s' repo.", self.name)
        self.obj.remotes.origin.pull(
            ref or self.default_ref, verbose=True, progress=GitProgressPrinter()
        )
        LOGGER.info("Completed pulling %s", self.name)

    @property
    def exists(self):
        """Convenience property to see if repo abject has been populated"""
        return self.obj is not None

    def get_tracked_paths(self, sections) -> Tuple[str]:
        """Get list of files from MAINTAINERS for given sections."""

        if self._tracked_paths is not None:
            return self._tracked_paths

        LOGGER.debug("Parsing MAINTAINERS file for %s", self.name)
        paths = set()

        # All tags starting with v4, also master.
        # TODO (Issue 66): This uses a hard-coded regex and relies on tags that may not be available
        refs = [
            tag
            for tag in self.obj.git.tag("v[^123]*", list=True).split()
            if re.match(r"v\d+\.+$", tag)
        ]
        refs.append(f"origin/{self.default_ref}")  # Include default reference

        for ref in refs:
            paths |= extract_paths(sections, self.obj.git.show(f"{ref}:MAINTAINERS"))

        LOGGER.debug("Completed parsing MAINTAINERS file for %s", self.name)
        self._tracked_paths = tuple(sorted(paths))

        return self._tracked_paths

    def fetch_remote_ref(
        self, remote: str, local_ref: str, remote_ref: str, since: Optional[str] = None
    ) -> None:
        """
        Shallow fetch remote reference so it is available locally
        """

        remote = self.obj.remote(remote)

        # No fetch window specified
        if not since:
            LOGGER.info("Fetching ref %s from remote %s", remote_ref, remote)
            remote.fetch(remote_ref, verbose=True, progress=GitProgressPrinter())
            return

        # Initially fetch revision at depth 1
        LOGGER.info("Fetching remote ref %s from remote %s at depth 1", remote_ref, remote)
        fetch_info = remote.fetch(remote_ref, depth=1, verbose=True, progress=GitProgressPrinter())

        # If last commit for revision is in the fetch window, expand depth
        # This check is necessary because some servers will throw an error when there are
        # no commits in the fetch window
        if fetch_info[-1].commit.committed_date >= approxidate.approx(since):
            LOGGER.info(
                'Fetching ref %s from remote %s shallow since "%s"',
                remote_ref,
                remote,
                since,
            )
            try:
                remote.fetch(
                    remote_ref,
                    shallow_since=since,
                    verbose=True,
                    progress=GitProgressPrinter(),
                )
            except git.GitCommandError as e:
                # ADO repos do not currently support --shallow-since, only depth
                if "Server does not support --shallow-since" in e.stderr:
                    LOGGER.warning(
                        "Server does not support --shallow-since, retrying fetch without option."
                    )
                    remote.fetch(remote_ref, verbose=True, progress=GitProgressPrinter())
                else:
                    raise
        else:
            LOGGER.info(
                'Newest commit for ref %s from remote %s is older than fetch window "%s"',
                remote_ref,
                remote,
                since,
            )

        # Create tag at FETCH_HEAD to preserve reference locally
        if not hasattr(self.obj.references, local_ref):
            self.obj.create_tag(local_ref, "FETCH_HEAD")

    def get_missing_cherries(self, reference, paths, since: Optional[str] = None):
        """
        Get a list of cherry-picked commits missing from the downstream reference
        """

        args = ["--no-merges", "--pretty=format:%H"]
        if since:
            args.append(f"--since={since}")

        # Get all upstream commits on tracked paths within window
        upstream_commits = set(
            self.obj.git.log(
                *args,
                f"origin/{self.default_ref}",
                "--",
                paths,
            ).splitlines()
        )

        # Get missing cherries for all paths, but don't filter by path since it takes forever
        missing_cherries = set(
            self.obj.git.log(
                *args,
                "--right-only",
                "--cherry-pick",
                f"{reference}...origin/{self.default_ref}",
            ).splitlines()
        )

        return missing_cherries & upstream_commits

    def get_remote_tags(self, remote: str):
        """
        List tags for a given remote in the format tags/TAGNAME
        """

        return tuple(
            line.split("/", 1)[-1]
            for line in self.obj.git.ls_remote(
                "--tags", "--refs", "--sort=v:refname", remote
            ).splitlines()
        )

    def checkout(self, reference):
        """
        Checkout the given reference
        """

        # Use the reference object directly if it was given
        if isinstance(reference, git.Reference):
            self.obj.head.reference = reference

        # If the reference is a known reference, use it
        elif reference in self.obj.references:
            self.obj.head.reference = self.obj.references[reference]

        # Otherwise, treat as a commit
        else:
            self.obj.head.reference = self.obj.commit(reference)

        # Reset head
        self.obj.head.reset(index=True, working_tree=True)


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


class GitProgressPrinter(git.RemoteProgress):
    """
    Simple status printer for GitPython
    """

    def update(self, op_code, cur_count, max_count=None, message=""):
        """
        Subclassed from parent. Called for each line in output.
        """
        if not LOGGER.isEnabledFor(logging.INFO):
            return

        print(f"  {self._cur_line}", end="    ")
        if op_code & self.END:
            print()
        else:
            print("\r", end="", flush=True)
