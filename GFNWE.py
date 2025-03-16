import os
from os.path import basename
def getFileNameWithoutExtension(files):
    fname = os.path.basename(files)
    base1 = os.path.splitext(fname)[0]
    return base1
