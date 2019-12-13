'''
list_diff gives list1 - list2 = items in list1 which are not present in list2
params: 2 lists
return: list
'''
def list_diff(list1, list2):
    return (list(set(list1)-set(list2)))

'''
contains_filepath checks if file1 is contained in filepath of file2
'''
def contains_filepath(file1, file2):
    if file1.startswith('/'):
        file1 = file1[1:]
    if file2.startswith('/'):
        file2 = file2[1:]
    file_path_list1 = file1.split("/")
    file_path_list2 = file2.split("/")
    len1 = len(file_path_list1)
    len2 = len(file_path_list2)
    if len2 < len1-1:
        return False

    i=0

    for i in range (0,min(len1,len2)):
        if file_path_list1[i] != file_path_list2[i]:
            return False

    if i >= len1-2 and i == len2-1:
        return True
    else:
        return False

    