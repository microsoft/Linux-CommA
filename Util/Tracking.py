import logging

from Util.Config import paths_to_track


def get_tracked_paths(repo, revision="master"):
    """
    This function will parse maintainers file to get hyperV filenames

    repo: The git repository (git.repo object) to find the maintainers file at
    revision: Revision of the git repository to look at
    """
    logging.debug("Parsing maintainers files...")
    found_hyperv_block = False
    paths = []
    maintainers_file_content = repo.git.show(f"{revision}:MAINTAINERS")

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
                paths.append(file_path)
        # Check if we have reached the end of hyperv block
        if found_hyperv_block and line == "":
            break
    logging.debug("Parsed!")
    # TODO: Remove duplicates and validate
    paths.extend(paths_to_track)
    assert paths is not None
    return paths
