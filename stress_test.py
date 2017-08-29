#!/usr/bin/env python

import os
import sys
import time
from util import load_level


def test_file(path):
    level = load_level(path)


if __name__ == "__main__":
    start = time.time()
    with open("test_corpus.txt", "r") as input_file:
        corpus = input_file.readlines()

    paths = []
    for line in corpus:
        path = line.strip()
        if os.path.isdir(path):
            continue
        elif os.path.isfile(path):
            paths.append(path)
        else:
            print "Skipping %s" % path

    failures = []
    for path in paths:
        try:
            test_file(path)
        except:
            failures.append(path)    

    end = time.time()
    elapsed = end - start
    print "Took {} seconds to parse {} files.".format(elapsed, len(paths))

    if failures:
        print " - %s files raised an exception." % len(failures)
        with open("test_failures.txt", "w") as out_file:
            out_file.write("\n".join(failures))
        print " - see test_failures.txt"
