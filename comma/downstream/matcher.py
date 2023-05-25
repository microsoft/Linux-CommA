# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Functions to compare commits for similarities
"""

import logging
import os
from typing import Iterable, List

from fuzzywuzzy import fuzz

from comma.database.model import PatchData
from comma.util import PatchDiff


# Confidence weights
AUTHOR_WEIGHT = 0.2
AUTHOR_DATE_WEIGHT = 0.01  # This addresses some edge cases of identical other fields
COMMIT_DATE_WEIGHT = 0.01  # This addresses some edge cases of identical other fields
DESCRIPTION_WEIGHT = 0.1
FILENAMES_WEIGHT = 0.2
SUBJECT_WEIGHT = 0.48

CONFIDENCE_THRESHOLD = 0.75  # Threshold that we must hit to return a match


def calculate_filenames_confidence(
    downstream_filepaths: Iterable[str], upstream_filepaths: Iterable[str]
) -> float:
    """
    Calculate filenames confidence
    Roughly the percent of upstream filepaths present in downstream filepaths
    """

    # If they are the same, for example empty, confidence is high
    if downstream_filepaths == upstream_filepaths:
        return 1.0

    # If only one is empty, confidence is low
    if "" in (downstream_filepaths, upstream_filepaths):
        return 0.0

    total_filepaths_match = 0
    downstream_file_components = [os.path.split(filepath) for filepath in downstream_filepaths]

    for upstream_path, upstream_name in (
        os.path.split(filepath) for filepath in upstream_filepaths
    ):
        max_match = 0.0
        # Find best matching downstream filepath
        for downstream_path, downstream_name in downstream_file_components:
            if upstream_name != downstream_name:
                continue
            # 0.5 for matching filename
            # The paths are fuzzymatched scaled 0.0-0.5 for remaining match
            match = 0.5 + (fuzz.partial_ratio(upstream_path, downstream_path) / 200.0)
            if match > max_match:
                max_match = match
        total_filepaths_match += max_match

    return total_filepaths_match / len(upstream_filepaths)


def patch_matches(downstream_patches: List[PatchData], upstream: PatchData) -> bool:
    """Check if 'upstream' has an equivalent in 'downstream_patches'."""

    # Preprocessing for matching filenames
    upstream_filepaths = upstream.affectedFilenames.split(" ")

    logging.debug("Upstream missing patch, %s", upstream.commitID)
    for downstream in downstream_patches:
        # Calculate confidence that our upstream patch matches this downstream patch

        author_confidence = fuzz.token_set_ratio(upstream.author, downstream.author) / 100.0
        author_date_confidence = 1.0 if upstream.authorTime == downstream.authorTime else 0.0
        commit_date_confidence = 1.0 if upstream.commitTime == downstream.commitTime else 0.0
        # Temporarily for description only checking exact string is in
        description_confidence = 1.0 if upstream.description in downstream.description else 0.0
        filenames_confidence = calculate_filenames_confidence(
            downstream.affectedFilenames.split(" "), upstream_filepaths
        )
        subject_confidence = fuzz.partial_ratio(upstream.subject, downstream.subject) / 100.0

        if (
            AUTHOR_WEIGHT * author_confidence
            + AUTHOR_DATE_WEIGHT * author_date_confidence
            + COMMIT_DATE_WEIGHT * commit_date_confidence
            + DESCRIPTION_WEIGHT * description_confidence
            + FILENAMES_WEIGHT * filenames_confidence
            + SUBJECT_WEIGHT * subject_confidence
        ) >= CONFIDENCE_THRESHOLD:
            return True

    # TODO just do this part?...
    # Check for code matching
    upstream_diffs = PatchDiff(upstream.commitDiffs)
    return any(
        upstream_diffs.percent_present_in(PatchDiff(downstream.commitDiffs)) > CONFIDENCE_THRESHOLD
        for downstream in downstream_patches
    )
