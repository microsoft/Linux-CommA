from fuzzywuzzy import fuzz

from Objects.PatchDiffs import PatchDiffs


class DownstreamMatcher:
    def __init__(self, downstream_patches):

        """
        downstream_patches is a list of Patch objects
        """
        self.downstream_patches = downstream_patches

    def exists_matching_patch(self, upstream_patch):
        """
        upstream_patch is a Patch object to match to downstream
        Returns: True if there exists this upstream_patch equivilent in our downstream patches
        """

        # Confidence weights
        author_weight = 0.2
        subject_weight = 0.48
        description_weight = 0.1
        filenames_weight = 0.2
        author_date_weight = (
            0.01  # This addresses some edge cases of identical other fields
        )
        commit_date_weight = (
            0.01  # This addresses some edge cases of identical other fields
        )

        # Threshold that we must hit to return a match
        threshold = 0.75

        # Preprocessing for matching filenames
        upstream_filepaths = upstream_patch.affectedFilenames.split(" ")
        upstream_file_components = [
            _get_filepath_components(filepath) for filepath in upstream_filepaths
        ]

        for downstream_patch in self.downstream_patches:
            # Calculate confidence that our upstream patch matches this downstream patch

            # Calculate filenames confidence, which is roughly the percent of upstream filepaths present in downstream patch
            if (
                downstream_patch.affectedFilenames == ""
                or upstream_patch.affectedFilenames == ""
            ):
                filenames_confidence = (
                    1.0
                    if (
                        downstream_patch.affectedFilenames
                        == upstream_patch.affectedFilenames
                    )
                    else 0.0
                )
            else:
                total_filepaths_match = 0
                downstream_filepaths = downstream_patch.affectedFilenames.split(" ")
                downstream_file_components = [
                    _get_filepath_components(filepath)
                    for filepath in downstream_filepaths
                ]

                for (upstream_path, upstream_name) in upstream_file_components:
                    max_match = 0.0
                    # Find best matching downstream filepath
                    for (
                        downstream_path,
                        downstream_name,
                    ) in downstream_file_components:
                        if upstream_name == downstream_name:
                            # 0.5 for matching filename, the paths are fuzzymatched scaled 0.0-0.5 for remaining match
                            match = 0.5 + (
                                fuzz.partial_ratio(upstream_path, downstream_path)
                                / 200.0
                            )
                        else:
                            match = 0.0

                        if match > max_match:
                            max_match = match
                    total_filepaths_match += max_match

                filenames_confidence = float(total_filepaths_match) / len(
                    upstream_filepaths
                )

            author_confidence = (
                fuzz.token_set_ratio(upstream_patch.author, downstream_patch.author)
                / 100.0
            )
            subject_confidence = (
                fuzz.partial_ratio(upstream_patch.subject, downstream_patch.subject)
                / 100.0
            )
            # Temporarily for description only checking exact string is in
            if upstream_patch.description == "":
                description_confidence = (
                    1.0 if downstream_patch.description == "" else 0.0
                )
            else:
                description_confidence = (
                    1.0
                    if upstream_patch.description in downstream_patch.description
                    else 0.0
                )
            author_date_confidence = (
                1.0 if upstream_patch.authorTime == downstream_patch.authorTime else 0.0
            )
            commit_date_confidence = (
                1.0 if upstream_patch.commitTime == downstream_patch.commitTime else 0.0
            )

            confidence = (
                author_weight * author_confidence
                + subject_weight * subject_confidence
                + description_weight * description_confidence
                + filenames_weight * filenames_confidence
                + author_date_confidence * author_date_weight
                + commit_date_confidence * commit_date_weight
            )
            if confidence >= threshold:
                return True

        # TODO just do this part?...
        # Check for code matching
        upstream_diffs = PatchDiffs(upstream_patch.commitDiffs)
        for downstream_patch in self.downstream_patches:
            downstream_diffs = PatchDiffs(downstream_patch.commitDiffs)
            code_match_confidence = upstream_diffs.percent_present_in(downstream_diffs)
            if code_match_confidence > threshold:
                return True

        return False


def _get_filepath_components(filepath):
    """
    Splits filepath to return (path, filename)
    """
    components = filepath.rsplit("/", 1)
    if len(components) == 1:
        return (None, components[0])
    return (components[0], components[1])
