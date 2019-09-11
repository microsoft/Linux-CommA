
class DownstreamMatcher:
    
    def __init__(upstream_patches):
        """
        Creates the DownstreamMatcher.
        upstream_patches is a list of Patch objects from upstream we will check against
        """
        self.upstream_patches = upstream_patches



    def get_matching_patch(downstream_patch):
        """
        downstream_patch is a Patch object to match to upstream
        Returns: DistroPatchMatch, or None of no confidence match found
        """

        # define confidence weights
        author_match = 0



        best_match_patch = None
        best_match_conf = 0.0
        best_match_author_conf = 0.0
        best_match_subject_conf = 0.0
        best_match_description_conf = 0.0
        best_match_filenames_conf = 0.0

        # for patch in upstream_patches:
            # if 

        return None


















