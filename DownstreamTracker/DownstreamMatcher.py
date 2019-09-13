
from fuzzywuzzy import fuzz
from Objects.DistroPatchMatch import DistroPatchMatch

class DownstreamMatcher:
    upstream_patches = {}

    def __init__(self, up_db):

        """
        Creates the DownstreamMatcher.
        upstream_patches is a list of UpstreamPatch class
        """
        self.upstream_patches = up_db.get_upstream_patch()



    def get_matching_patch(self, downstream_patch):
        """
        downstream_patch is a Patch object to match to upstream
        Returns: DistroPatchMatch, or None of no confidence match found
        """

        # Define confidence weights
        best_patch_id = -1
        best_confidence = 0.0
        best_author_confidence = 0.0
        best_subject_confidence = 0.0
        best_description_confidence = 0.0
        best_filenames_confidence = 0.0

        # Confidence weights
        author_weight = 0.3
        subject_weight = 0.3
        description_weight = 0.1
        filenames_weight = 0.3

        # Threshold that we must hit to return a match
        threshold = 0.0

        for Upstream_patch in self.upstream_patches:
            # Calculate confidence that our downstream patch matches this upstream patch

            # Calculate filenames confidence, which is the percentage of files upstream that are present in the downstream patch
            num_filenames_match = 0
            upstream_filenames = tuple(Upstream_patch.filenames)
            for downstream_filename in downstream_patch.filenames:
                if (downstream_filename.endswith(upstream_filenames)):
                    num_filenames_match += 1
            filenames_confidence = float(num_filenames_match) / len(Upstream_patch.filenames)

            author_confidence = fuzz.partial_ratio(Upstream_patch.author_name, downstream_patch.author_name) / 100.0
            subject_confidence = fuzz.partial_ratio(Upstream_patch.subject, downstream_patch.subject) / 100.0
            # Temporarily for description only checking exact string is in
            description_confidence = 1.0 if Upstream_patch.description in downstream_patch.description else 0.0

            confidence = author_weight*author_confidence + subject_weight*subject_confidence + description_weight*description_confidence + filenames_weight*filenames_confidence
            if confidence > best_confidence:
                best_patch_id = Upstream_patch.patch_id
                best_confidence = confidence
                best_author_confidence = author_confidence
                best_subject_confidence = subject_confidence
                best_description_confidence = description_confidence
                best_filenames_confidence = filenames_confidence
            elif (confidence == best_confidence):
                print("[info] Two patches found with same confidence")

        if best_confidence < threshold:
            return None

        return DistroPatchMatch(best_author_confidence, best_subject_confidence, best_description_confidence, best_filenames_confidence, best_confidence, best_patch_id)




















