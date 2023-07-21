# -*- coding: utf-8 -*-

import configparser

parser = configparser.ConfigParser()
parser.read("pyproject.toml")

__version__ = tuple(parser["tool.poetry"]["version"].strip("v\"'").split("."))
