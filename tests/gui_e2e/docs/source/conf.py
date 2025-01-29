#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""
# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from pathlib import Path

DIR_GUI_E2E = Path(__file__).parent.parent.parent
DIR_TESTLIB = DIR_GUI_E2E.parent / "testlib"
DIR_PLAYWRIGHT = DIR_TESTLIB / "playwright"

# -- Project information -----------------------------------------------------

project = "Framework: GUI end to end"
author = "Team-QA"

# -- General configuration ---------------------------------------------------
version = "0.0.1a"
release = "0.0.1a"


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "autoapi.extension",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# -- AutoAPI settings --------------------------------------------------------

autoapi_dirs = [DIR_GUI_E2E, DIR_PLAYWRIGHT]
autoapi_ignore = ["*/test_*.py", "*/conf.py", "*/.git"]
autoapi_keep_files = False
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_type = "python"
autodoc_typehints = "description"
autoapi_python_class_content = "class"
autoapi_python_use_implicit_namespaces = True
suppress_warnings = ["autoapi"]
