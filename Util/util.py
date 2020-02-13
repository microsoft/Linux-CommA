

def list_diff(list1, list2):
    """
    list_diff gives list1 - list2=items in list1 which are not present in list2
    params: 2 lists
    return: list
    """
    return (list(set(list1) - set(list2)))


def contains_filepath(filepath1, filepath2):
    """
    contains_filepath checks if file1 is contained in filepath of file2
    """
    return filepath2.startswith(filepath1)
