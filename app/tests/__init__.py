import os
from unittest import TextTestRunner
from unittest import defaultTestLoader as loader


def run():
    runner = TextTestRunner()

    this_dir = os.path.dirname(__file__)
    test_suite = loader.discover(start_dir=this_dir, pattern="*test*.py")

    runner.run(test_suite)
