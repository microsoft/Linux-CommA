
from fuzzywuzzy import fuzz
from Objects.DistroPatchMatch import DistroPatchMatch
from Objects.Diff_code import Diff_code

class DownstreamMatcher:
    upstream_patches = {}

    def __init__(self, up_db):

        """
        Creates the DownstreamMatcher.
        upstream_patches is a list of UpstreamPatch class
        """
        self.upstream_patches = up_db.get_upstream_patch()

    def get_matching_patch(self, downstream_patch, conf):
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
        best_code_match_confidence = 0.0

        # Confidence weights
        # author_weight = 0.2
        # subject_weight = 0.49
        # description_weight = 0.1
        # filenames_weight = 0.2
        # author_date_weight = 0.01 # This addresses some edge cases of identical other fields

        # Threshold that we must hit to return a match
        threshold = 0.75

        # Preprocessing for matching filenames
        downstream_filepaths = downstream_patch.filenames.split(" ")
        downstream_file_components = [_get_filepath_components(filepath) for filepath in downstream_filepaths]

        for upstream_patch in self.upstream_patches:
            # Calculate confidence that our downstream patch matches this upstream patch

            # Calculate filenames confidence, which is roughly the percent of upstream filepaths present downstream
            if (downstream_patch.filenames == "" or upstream_patch.filenames == ""):
                filenames_confidence = 1.0 if (downstream_patch.filenames == upstream_patch.filenames) else 0.0
            else:
                total_filepaths_match = 0
                upstream_filepaths = upstream_patch.filenames.split(" ")
                upstream_file_components = [_get_filepath_components(filepath) for filepath in upstream_filepaths]

                for (upstream_path, upstream_name) in upstream_file_components:
                    max_match = 0.0
                    # Find best matching downstream filepath
                    for (downstream_path, downstream_name) in downstream_file_components:
                        if (upstream_name == downstream_name):
                            # 0.5 for matching filename, the paths are fuzzymatched scaled 0.0-0.5 for remaining match
                            match = 0.5 + (fuzz.partial_ratio(upstream_path, downstream_path) / 200.0)
                        else:
                            match = 0.0

                        if match > max_match:
                            max_match = match
                    total_filepaths_match += max_match

                filenames_confidence = float(total_filepaths_match) / len(upstream_filepaths)

            author_confidence = fuzz.token_set_ratio(upstream_patch.author_name, downstream_patch.author_name) / 100.0
            subject_confidence = fuzz.partial_ratio(upstream_patch.subject, downstream_patch.subject) / 100.0
            # Temporarily for description only checking exact string is in
            if (upstream_patch.description == ""):
                description_confidence = 1.0 if downstream_patch.description == "" else 0.0
            else:
                description_confidence = 1.0 if upstream_patch.description in downstream_patch.description else 0.0
            author_date_confidence = 1.0 if upstream_patch.author_time == downstream_patch.author_time else 0.0

            confidence = conf.author_weight*author_confidence + conf.subject_weight*subject_confidence + conf.description_weight*description_confidence + conf.filenames_weight*filenames_confidence + author_date_confidence*conf.author_date_weight
            if confidence > best_confidence and confidence >= threshold:
                best_patch_id = upstream_patch.patch_id
                best_confidence = confidence
                best_author_confidence = author_confidence
                best_subject_confidence = subject_confidence
                best_description_confidence = description_confidence
                best_filenames_confidence = filenames_confidence
            elif (confidence == best_confidence):
                # TODO Check code matching in this case
                print("[info] Two patches found with same confidence")

        if best_confidence < threshold:
            for upstream_patch in self.upstream_patches:
                code_match_confidence = _get_code_matching(upstream_patch,downstream_patch)

                if code_match_confidence > best_code_match_confidence:
                    best_code_match_confidence = code_match_confidence
                    best_patch_id = upstream_patch.patch_id
                    best_confidence = code_match_confidence

        return DistroPatchMatch(best_author_confidence, best_subject_confidence, best_description_confidence, best_filenames_confidence, best_code_match_confidence, best_confidence, best_patch_id)

def _get_filepath_components(filepath):
    """
    Splits filepath to return (path, filename)
    """
    components = filepath.rsplit('/', 1)
    if (len(components) == 1):
        return (None, components[0])
    return (components[0], components[1])

'''

'''
def _get_code_matching(upstream, downstream):
    upstream_file_changes = _get_diff_code(upstream.diff)
    downstream_file_changes = _get_diff_code(downstream.diff)

    num_diff_match = 0
    for upstream_diff_code in upstream_file_changes:
        for downstream_diff_code in downstream_file_changes:
            if upstream_diff_code == downstream_diff_code:
                num_diff_match += 1
    
    return num_diff_match/len(upstream_file_changes) if len(upstream_file_changes) != 0 else 0

'''
build array of diff_code objects from string
'''
def _get_diff_code(diff):
    tokens = diff.strip().split('\n')
    arr_diff_code = []
    diff_code = Diff_code("","","")
    for i in range(0,len(tokens)):
        if tokens[i].startswith('+'):
            diff_code.diff_add=tokens[i] if len(diff_code.diff_add)==0 else "\n"+tokens[i]
        elif tokens[i].startswith('-'):
            diff_code.diff_remove=tokens[i] if len(diff_code.diff_remove) == 0 else "\n"+tokens[i]
        else:
            if not diff_code.is_empty():
                arr_diff_code.append(diff_code)
            diff_code = Diff_code(tokens[i],"","")
    return arr_diff_code

