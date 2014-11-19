import os


def list_directory(dirname):
    # List the files in the directory, and sort them
    files = os.listdir(dirname)
    # Filter out files with leading .
    return [f for f in files if f[0] != '.']
