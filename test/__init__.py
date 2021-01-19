import glob
import os

__all__ = ['TAR_FILE']

tar_files = sorted(glob.glob(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '*.tar'))))
TAR_FILE = tar_files[min(1, len(tar_files))]
tar_files = None
