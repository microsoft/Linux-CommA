# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions and classes for fetching and parsing data from Git
"""

import logging
import pathlib
from typing import Any, List, Optional
from urllib.parse import urlparse

import git

from comma.util import DateString


LOGGER = logging.getLogger(__name__)


class GitRetry:
    """
    Specific wrapper for git functions
    Looks for common errors in output and retries, otherwise raises
    """

    errors = (
        "fatal: expected 'acknowledgments'",
        "The requested URL returned error: 500",
    )

    def __init__(self, func: callable, max_tries: int = 3):
        self.func = func
        self.max_tries = max_tries

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        for tries in range(1, self.max_tries + 1):
            try:
                # Call function with provided arguments
                return self.func(*args, **kwargs)
            except git.GitCommandError as e:
                # Raise if retries are exhausted
                if tries >= self.max_tries:
                    LOGGER.error(
                        "Function call (%r) exceeded maximum tries (%d): args=%r, kwargs=%r",
                        self.func,
                        self.max_tries,
                        args,
                        kwargs,
                    )
                    raise

                # Retry on known errors
                if any(error in e.stderr for error in self.errors):
                    LOGGER.warning("Likely transient error, retrying: %s", e)

                else:
                    # Raise on anything else
                    raise

        # We should never get here
        raise RuntimeError("Unexpectedly exited loop!")


def get_filenames(commit: git.Commit) -> List[str]:
    """
    Get all paths affected by a given commit
    """

    if not commit.parents:
        return []
    diffs = commit.tree.diff(commit.parents[0])
    # Sometimes a path is in A and not B but we want all filenames.
    return sorted(
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

    def fetch_remote_ref(
        self, remote: str, local_ref: str, remote_ref: str, since: Optional[DateString] = None
    ) -> None:
        """
        Shallow fetch remote reference so it is available locally
        """

        local_sha = None
        remote_sha = None
        kwargs = {"verbose": True, "progress": GitProgressPrinter()}
        remote = self.obj.remote(remote)
        fetch = GitRetry(remote.fetch)

        # Check if we already have a local reference
        if hasattr(self.obj.references, local_ref):
            local_ref_obj = self.obj.references[local_ref]
            local_sha = (
                local_ref_obj.object.hexsha
                if hasattr(local_ref_obj, "object")
                else local_ref_obj.commit.hexsha
            )

            # If we have the ref locally, we still want to update, but give negotiation hint
            kwargs["negotiation_tip"] = local_ref

            # Get remote ref so we can check against the local ref
            if output := self.obj.git.ls_remote(remote, remote_ref):
                remote_sha = output.split()[0]

        # No fetch window specified
        # Or using Azure DevOps since it doesn't support shallow-since or unshallow
        if not since or any(
            urlparse(url).hostname == "msazure.visualstudio.com" for url in remote.urls
        ):
            LOGGER.info("Fetching ref %s from remote %s", remote_ref, remote)
            fetch(remote_ref, **kwargs)

            # Create tag at FETCH_HEAD to preserve reference locally
            if local_sha is None or local_sha != remote_sha:
                self.obj.create_tag(local_ref, "FETCH_HEAD", force=True)

            return

        # If we have the ref locally, see if the ref is the same to avoid resetting depth
        if local_sha and remote_sha == local_sha:
            commit_date = self.obj.references[local_ref].commit.committed_date

        # Otherwise, initially fetch revision at depth 1. This will reset local depth
        else:
            LOGGER.info("Fetching remote ref %s from remote %s at depth 1", remote_ref, remote)
            fetch_info = fetch(remote_ref, depth=1, **kwargs)[-1]
            commit_date = fetch_info.commit.committed_date

        # If last commit for revision is in the fetch window, expand depth
        # This check is necessary because some servers will throw an error when there are
        # no commits in the fetch window
        if commit_date >= since.epoch:
            LOGGER.info(
                'Fetching ref %s from remote %s shallow since "%s"',
                remote_ref,
                remote,
                since,
            )
            try:
                fetch(remote_ref, shallow_since=since, **kwargs)
            except git.GitCommandError as e:
                # ADO repos do not currently support --shallow-since, only depth
                if "Server does not support --shallow-since" in e.stderr:
                    LOGGER.warning(
                        "Server does not support --shallow-since, retrying fetch without option."
                    )
                    fetch(remote_ref, **kwargs)
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
        if local_sha is None or local_sha != remote_sha:
            self.obj.create_tag(local_ref, "FETCH_HEAD", force=True)

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
