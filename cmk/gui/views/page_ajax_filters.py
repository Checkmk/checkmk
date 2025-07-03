#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.data_source import data_source_registry
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.output_funnel import output_funnel

from .store import get_permitted_views


class ABCAjaxInitialFilters(AjaxPage):
    @abc.abstractmethod
    def _get_context(self, page_name: str) -> VisualContext:
        raise NotImplementedError()

    def page(self, config: Config) -> dict[str, str]:
        api_request = self.webapi_request()
        varprefix = api_request.get("varprefix", "")
        page_name = api_request.get("page_name", "")
        context = self._get_context(page_name)
        page_request_vars = api_request.get("page_request_vars")
        assert isinstance(page_request_vars, dict)
        vs_filters = visuals.VisualFilterListWithAddPopup(info_list=page_request_vars["infos"])
        with output_funnel.plugged():
            vs_filters.render_input(varprefix, context)
            return {"filters_html": output_funnel.drain()}


class AjaxInitialViewFilters(ABCAjaxInitialFilters):
    def get_context(self, page_name: str) -> VisualContext:
        return self._get_context(page_name)

    def _get_context(self, page_name: str) -> VisualContext:
        # Obtain the visual filters and the view context
        view_name = page_name
        try:
            view_spec = get_permitted_views()[view_name]
        except KeyError:
            raise MKUserError("view_name", _("The requested item %s does not exist") % view_name)

        datasource = data_source_registry[view_spec["datasource"]]()
        show_filters = visuals.filters_of_visual(
            view_spec, datasource.infos, link_filters=datasource.link_filters
        )

        view_context = view_spec.get("context", {})
        current_context = self.webapi_request().get("context")

        # If single info keys are missing in the spec context take them from the current context
        single_info_keys = visuals.get_missing_single_infos(view_spec["single_infos"], view_context)
        if single_info_keys and current_context is not None:
            view_context = {
                **view_context,
                **{k: current_context[k] for k in single_info_keys if k in current_context},
            }

        # Return a visual filters dict filled with the view context values
        return {f.ident: view_context.get(f.ident, {}) for f in show_filters if f.available()}
