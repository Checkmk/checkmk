#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import datetime

DOC_ROOT = os.path.dirname(__file__)

sys.path.insert(0, os.path.join(DOC_ROOT, "..", ".."))


# -- Project information -----------------------------------------------------

year = datetime.now().year
project = "CheckMK"
author = "Checkmk GmbH"
copyright = f"{year}, {author}"  # noqa: A001


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib.spelling",
    "sphinxcontrib.plantuml",
]

plantuml_path = os.getenv("PLANTUML_JAR_PATH")
if not plantuml_path:
    raise Exception("PLANTUML_JAR_PATH must be defined")

plantuml = " ".join(
    [
        "java",
        "-Djava.awt.headless=true",
        "-jar",
        os.path.join(
            plantuml_path,
            "plantuml.jar",
        ),
    ]
)

plantuml_output_format = "svg"

spelling_show_suggestions = True
spelling_warning = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

language = "en"

# Replaces e.g. "Checkmk's" with characters that can not correctly be rendered
# in htmlhelp in all cases
smartquotes = False
