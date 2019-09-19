
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
        author_weight = 0.2
        subject_weight = 0.5
        description_weight = 0.1
        filenames_weight = 0.2

        # Threshold that we must hit to return a match
        threshold = 0.75

        for upstream_patch in self.upstream_patches:
            # Calculate confidence that our downstream patch matches this upstream patch

            # Calculate filenames confidence, which is the percentage of files upstream that are present in the downstream patch

            if (downstream_patch.filenames == ""):
                filenames_confidence = 0.0
            else:
                num_filenames_match = 0
                upstream_patch_filenames = upstream_patch.filenames.split(" ")
                upstream_patch_filenames_tuple = tuple(upstream_patch_filenames)
                downstream_patch_filenames = downstream_patch.filenames.split(" ")
                for downstream_filename in downstream_patch_filenames:
                    if (downstream_filename.endswith(upstream_patch_filenames_tuple)):
                        num_filenames_match += 1
                filenames_confidence = float(num_filenames_match) / len(upstream_patch_filenames)

            author_confidence = fuzz.token_set_ratio(upstream_patch.author_name, downstream_patch.author_name) / 100.0
            subject_confidence = fuzz.partial_ratio(upstream_patch.subject, downstream_patch.subject) / 100.0
            # Temporarily for description only checking exact string is in
            description_confidence = 1.0 if upstream_patch.description in downstream_patch.description else 0.0

            confidence = author_weight*author_confidence + subject_weight*subject_confidence + description_weight*description_confidence + filenames_weight*filenames_confidence
            if confidence > best_confidence and confidence >= threshold:
                best_patch_id = upstream_patch.patch_id
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




















