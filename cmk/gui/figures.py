#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Basic functions for cmk_figures

import abc
import json
from typing import Type, Dict, Any

from cmk.gui.plugins.dashboard import Dashlet
from cmk.gui.globals import html

FigureResponse = Dict[str, Any]


def create_figures_response(data, context=None) -> FigureResponse:
    """ Any data for a figure is always wrapped into a dictionary
        This makes future extensions (meta_data, etc.) easier, preventing
        intermingling of dictionary keys """
    response = {"figure_response": data}
    if context:
        response["context"] = context
    return response


class ABCDataGenerator(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def vs_parameters(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def generate_response_data(cls, properties, context):
        raise NotImplementedError()

    @classmethod
    def generate_response_from_request(cls):
        properties = cls.vs_parameters().value_from_json(
            json.loads(html.request.get_str_input_mandatory("properties")))
        context = json.loads(html.request.get_str_input_mandatory("context", "{}"))
        response_data = cls.generate_response_data(properties, context)
        return create_figures_response(response_data)


class ABCFigureDashlet(Dashlet, metaclass=abc.ABCMeta):
    """ Base class for cmk_figures based graphs
        Only contains the dashlet spec, the data generation is handled in the
        DataGenerator classes, to split visualization and data
    """
    @classmethod
    def type_name(cls):
        return "figure_dashlet"

    @classmethod
    def sort_index(cls):
        return 95

    @classmethod
    def initial_refresh_interval(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (56, 40)

    @classmethod
    def default_settings(cls):
        return {"show_title": False}

    @classmethod
    def infos(cls):
        return ["host", "service"]

    @classmethod
    def single_infos(cls):
        return []

    @classmethod
    def has_context(cls):
        return True

    @property
    def instance_name(self):
        # Note: This introduces the restriction one graph type per dashlet
        return "%s_%s" % (self.type_name(), self._dashlet_id)

    @classmethod
    def vs_parameters(cls):
        return cls.data_generator().vs_parameters()

    @classmethod
    @abc.abstractmethod
    def data_generator(cls) -> Type[ABCDataGenerator]:
        raise NotImplementedError()

    @property
    def update_interval(self):
        return 60

    def on_resize(self):
        return ("if (typeof %(instance)s != 'undefined') {"
                "%(instance)s.resize();"
                "%(instance)s.render();"
                "}") % {
                    "instance": self.instance_name
                }


class TableFigureDataCreator:
    """ Helps to create the data shown in a table_figure.js figure
        The javascript TableFigure supports partial data updates and the integration of dc.js pie charts within cells
        {
          "classes": ["classes", "for", "table"],              // classes for this table
          "rows": [
             [ {                                               // Dict, representing a row
                 "classes": ["classes", "for", "row"],         // classes for this row
                 "cells": [ {                                  // Dict, representing a cell. All keys are optional
                   "text": "Text to display",
                   "html": "HTML to to display",               // overrules "text" key
                   "cell_type": "td"                           // supports td and th
                   "classes": ["classes", "for", "cell"],      // classes for this cell
                   "rowspan": 1,
                   "colspan": 3,
                   "figure_config": {figure_definition}        // cell with figure config, including data
                 } ]
             ], ...
             }
          ]
        }
    """
    @classmethod
    def get_header_cell(cls, text, attrs=None, classes=None):
        cell = {"text": text}
        attrs = {} if attrs is None else attrs
        attrs["cell_type"] = "th"
        cell.update(cls.compute_attr_and_classes(attrs, classes))
        return cell

    @classmethod
    def get_text_cell(cls, text, attrs=None, classes=None):
        cell = {"text": text}
        cell.update(cls.compute_attr_and_classes(attrs, classes))
        return cell

    @classmethod
    def get_html_cell(cls, html_content, attrs=None, classes=None):
        cell = {"html": html_content}
        cell.update(cls.compute_attr_and_classes(attrs, classes))
        return cell

    # Cell with text or html content, only used for classes and attr
    # This cell is generally used by graphs
    @classmethod
    def get_empty_cell(cls, attrs=None, classes=None):
        return cls.compute_attr_and_classes(attrs, classes)

    @classmethod
    def compute_attr_and_classes(cls, attrs, classes):
        extra = {}
        attrs = {} if attrs is None else attrs
        for key, value in attrs.items():
            extra[key] = value
        if classes:
            extra["classes"] = classes
        return extra

    # Cell which contains a dc graphing element
    @classmethod
    def get_figure_cell(cls, figure_config, attrs=None, classes=None):
        classes = classes or []
        classes.append("figure_cell")
        attrs = attrs or {}
        attrs["id"] = figure_config["id"]
        cell = cls.get_empty_cell(attrs, classes)
        figure_config["selector"] = "#%s" % figure_config["id"]
        cell["figure_config"] = figure_config
        return cell

    @classmethod
    def get_pie_chart_config(cls, attr_id, data, title=None):
        """ Generates the configuration for a pie chart diagram
            The actual percentage values are calculated in js
            [
              {"label1": "test", "value": 23},
              {"label2": "test2, "value": 42}
                ....
            ]
        """
        return {"id": attr_id, "type": "pie_chart", "title": title, "data": data}
