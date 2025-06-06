#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

import logging
import os
import sys

sys.path.insert(0, os.path.abspath("../../../"))
sys.path.insert(0, os.path.abspath("../../../packages/cmk-plugin-apis"))

# -- Project information -----------------------------------------------------

project = "Checkmk's Plug-in APIs"
copyright = "2023, Checkmk GmbH"  # noqa: A001
author = "Checkmk GmbH"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
]

# Ignore unneeded dependencies during sphinx doc build time for now.
#
# The better way to deal with it would be to create a dedicated venv for the plugin API doc
# generator which pulls in our packages as dependencies. This way we would ensure that all
# dependencies are available during the sphinx execution. But since the documented modules
# cmk.base.plugins.bakery.bakery_api and
# cmk.cee.dcd.plugins.connectors.connectors_api
# are not separate packages right now, we can not move on with this.
autodoc_mock_imports = [
    "cmk.trace",
    "livestatus",
    "cryptography",
]

suppress_warnings = [
    # Our v1 and v2 APIs expose Result and Metric which is totally fine. Silence the warning.
    "ref.python",
]

# The warnings "*:docstring of cmk.agent_based.v1._value_store_utils.GetRateError:1: WARNING:
# duplicate object description of cmk.agent_based.v1._value_store_utils.GetRateError, other instance
# in cmk.agent_based/v1, use :no-index: for one of them" is similar to the warning suppressed above
# and built like this intentionally. Since this warning can not be suppressed using the sphinx
# suppress_warnings feature we filter out the log message.
logging.getLogger("sphinx").addFilter(
    lambda s: "duplicate object description of cmk.agent_based.v1" not in s.getMessage()
)

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = []

# Instead of absolute module names like "cmk.gui.plugins.dashboard.dashboard_api.v0.IFrameDashlet",
# that fill the whole page, use the plain module local names of the classes.
add_module_names = False
autodoc_default_options = {
    "member-order": "bysource",
    "exclude-members": "to_json, from_json, serialize, deserialize",
}
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Do not render the "View page source" links on all doc pages
html_show_sourcelink = False

# Theme specific options (see https://sphinx-rtd-theme.readthedocs.io/en/latest/configuring.html)

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
