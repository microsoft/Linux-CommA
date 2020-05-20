import logging

from Util.Config import filepaths_to_track


def get_tracked_paths(repo, revision="master"):
    """
    This function will parse maintainers file to get hyperV filenames

    repo: The git repository (git.repo object) to find the maintainers file at
    revision: Revision of the git repository to look at
    """
    logging.debug("Parsing maintainers files...")
    found_hyperv_block = False
    file_names = []
    maintainers_file_content = repo.git.show("%s:%s" % (revision, "MAINTAINERS"))

    for line in maintainers_file_content.split("\n"):
        if "Hyper-V CORE AND DRIVERS" in line:
            found_hyperv_block = True
        if found_hyperv_block and "F:\t" in line:
            words = line.strip().split()
            file_path = words[-1]
            # We wish to ignore any Documentation file, as those patches are not relevant.
            if (
                file_path is not None
                and len(file_path) != 0
                and "Documentation" not in file_path
            ):
                file_names.append(file_path)
        # Check if we have reached the end of hyperv block
        if found_hyperv_block and line == "":
            break
    logging.debug("Parsed!")
    # TODO: Remove duplicates and validate
    file_names.extend(filepaths_to_track)
    assert file_names is not None
    return file_names
