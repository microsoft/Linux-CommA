"""
This represents a match of a downstream distro commit to an upstream patch.
'confidence' is a stat ranging from 0..1 on how likely they are to be the same (with 1 being exactly the same)

"""


class DistroPatchMatch:
    def __init__(
        self,
        author_confidence,
        subject_confidence,
        description_confidence,
        filenames_confidence,
        code_match_confidence,
        confidence,
        upstream_patch_id,
    ):
        self.author_confidence = author_confidence
        self.subject_confidence = subject_confidence
        self.description_confidence = description_confidence
        self.filenames_confidence = filenames_confidence
        self.code_match_confidence = code_match_confidence
        self.confidence = confidence
        self.upstream_patch_id = upstream_patch_id
