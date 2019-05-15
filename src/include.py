""" That module contains handle_includes function
for recursive including XML files.
The function may be easily modified to handle
other types of files.
Written by Wojciech M. Zabolotny
wzab01<at>gmail.com
This is a free code (PUBLIC DOMAIN or CC0 1.0
Universal License). There is no warranty of any 
kind. You use it on your own risk!
"""
import os.path
import re
R1 = r"<!--\s*include\s*(?P<fname>\S+)\s*-->"
P1 = re.compile(R1)

def handle_includes(file_path,base_dir="./"):
    """ Function handle_includes replaces the include directives:
    <!-- include path/to/the/included_file -->
    with the contents of the included file.
    If the included file also contains include directives, they
    are handled recursively.
    The base_dir argument specifies base directory for relative
    paths.
    """
    # Check if the file_path is relative or absolute
    if file_path[0] == '/':
        # absolute
        full_file_path = file_path
    else:
        # relative
        full_file_path = base_dir + '/' + file_path
    # Read the file contents
    contents = open(full_file_path, 'r').read()
    # Create the base directory for possible further includes
    next_base_dir = os.path.dirname(full_file_path)
    # Find the include directives
    # Mark the start position
    start_pos = 0
    # List of the parts of the string
    chunks = []
    incl_iter = P1.finditer(contents)
    for incl_instance in incl_iter:
        # Find the occurence of include
        include_span = incl_instance.span()
        # Put the unmodified part of the string to the list
        chunks.append(contents[start_pos:include_span[0]])
        # Read the included file and handle nested includes
        replacement = handle_includes(incl_instance.groups()[0],next_base_dir)
        chunks.append(replacement)
        # Adjust the start position
        start_pos = include_span[1]
    # Add the final text (if any)
    chunks.append(contents[start_pos:])
    # Now create and return the content with resolved includes
    res = ''.join(chunks)
    return res

