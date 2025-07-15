#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry
from cmk.gui.type_defs import FilterName

from ._base import Filter


class FilterRegistry(Registry[Filter]):
    def __init__(self) -> None:
        super().__init__()
        self.htmlvars_to_filter: dict[str, FilterName] = {}

    def registration_hook(self, instance: Filter) -> None:
        # Know Exceptions, to this rule
        # siteopt is indistinguishable from site with the difference it
        # allows empty string.  This inverse mapping is to reconstruct
        # filters, from crosslinks, and in those we never set siteopt.
        # Because we use test first with may_add_site_hint. We set siteopt
        # over the filter menu, and there we already set the active flag.
        if instance.ident == "siteopt":
            return None

        # host_metrics_hist & svc_metrics_hist. These filters work at the
        # filter_table instant. We actually only need host_metric_hist, because
        # it has "host" info and thus, it is available in host & service infos.
        # However, the filter would only on the host filter menu. The poor
        # reason for duplication, is that as a post-processing filter, we
        # actually need to offer it on both host & service menus in case one of
        # those is a single context. It would be better to have post-processing
        # on a separte filter, as they aren't based on context.
        if instance.ident == "svc_metrics_hist":
            return None

        if any(
            self.htmlvars_to_filter.get(htmlvar, instance.ident) != instance.ident
            for htmlvar in instance.htmlvars
        ):
            # Will explode as soon as any dev tries to reuse htmlvars for different filters
            raise MKGeneralException(
                "Conflicting filter htmlvars: one of %r is already regitered" % instance.htmlvars
            )

        htmlvars_to_filter: Mapping[str, FilterName] = {
            htmlvar: instance.ident for htmlvar in instance.htmlvars
        }
        self.htmlvars_to_filter.update(htmlvars_to_filter)
        return None

    def plugin_name(self, instance):
        return instance.ident


filter_registry = FilterRegistry()
