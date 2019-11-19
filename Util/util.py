'''
list_diff gives list1 - list2 = items in list1 which are not present in list2
params: 2 lists
return: list
'''
def list_diff(list1, list2):
    return (list(set(list1)-set(list2)))