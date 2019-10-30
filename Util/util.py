
def list_diff(first, second):
    second = set(second)
    return [item for item in first if item not in second]
