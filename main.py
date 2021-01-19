#!/usr/bin/env python
from ucmexport import *
import logging
import glob
import os

from app import App

from time import perf_counter

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s: %(message)s')
    logging.getLogger('digit_analysis.node.traversal').setLevel(logging.INFO)
    logging.getLogger('user_dependency_graph').setLevel(logging.INFO)
    logging.getLogger('ucmexport').setLevel(logging.INFO)
    tar_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '*.tar'))
    tar_files = sorted(map(os.path.basename, tar_files))
    app = App(tar_files=tar_files)
    app.run()
    return


if __name__ == '__main__':
    main()
