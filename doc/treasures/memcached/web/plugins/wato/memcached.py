#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def memcached_upper_bounds(title, warn, crit, unit=None):
    spec_type = {int: Integer, float: Float, str: TextInput}
    return Tuple(title=title,
                 elements=[
                     spec_type[type(warn)](title=_("Warning at"), unit=unit, default_value=warn),
                     spec_type[type(warn)](title=_("Critical at"), unit=unit, default_value=crit),
                 ])


def memcached_lower_bounds(title, warn, crit, unit=None):
    spec_type = {int: Integer, float: Float, str: TextInput}
    return Tuple(title=title,
                 elements=[
                     spec_type[type(warn)](title=_("Warning below"), unit=unit, default_value=warn),
                     spec_type[type(warn)](title=_("Critical below"), unit=unit,
                                           default_value=crit),
                 ])


register_check_parameters(
    subgroup_applications,
    "memcached",
    _("Memcached"),
    Dictionary(
        title=_("Limits"),
        elements=[
            ('version', memcached_lower_bounds("Version", "1.4.15", "1.4.15")),
            ('rusage_system', memcached_upper_bounds("System CPU time used", 0, 0, u"s")),
            ('rusage_user', memcached_upper_bounds("User CPU time used", 0, 0, u"s")),
            ('threads', memcached_upper_bounds("Number of threads used", 0, 0)),
            ('auth_cmds', memcached_upper_bounds("Number of authentication commands", 0, 0)),
            ('auth_errors', memcached_upper_bounds("Number of authentication errors", 0, 0)),
            ('bytes_percent', memcached_upper_bounds("Cache Usage", 0.8, 0.9, _("percent"))),
            ('bytes_read', memcached_upper_bounds("Bytes Read", 0, 0)),
            ('bytes_written', memcached_upper_bounds("Bytes Written", 0, 0)),
            ('curr_items', memcached_upper_bounds("Number of items in cache", 0, 0)),
            ('evictions',
             memcached_upper_bounds("Number of objects removed to free up memory", 100, 200)),
            ('get_hits', memcached_upper_bounds("Number of successful 'get' commands", 0, 0)),
            ('get_misses', memcached_upper_bounds("Number of failed 'get' commands", 0, 0)),
            ('total_connections',
             memcached_upper_bounds("Number of connections since server start", 0, 0)),
            ('total_items', memcached_upper_bounds("Number of items stored on the server", 0, 0)),
            ('cache_hit_rate', memcached_lower_bounds("Rate of cache hits", 0.9, 0.8,
                                                      _("percent"))),
            ('cas_badval', memcached_upper_bounds("CAS fails due to bad identifier", 5, 10)),
            ('cas_hits', memcached_upper_bounds("CAS hits", 0, 0)),
            ('cas_misses', memcached_upper_bounds("CAS misses", 0, 0)),
            ('cmd_flush', memcached_upper_bounds("Number of 'flush_all' commands", 1, 5)),
            ('cmd_get', memcached_upper_bounds("Number of 'get' commands", 0, 0)),
            ('cmd_set', memcached_upper_bounds("Number of 'set' commands", 0, 0)),
            ('connection_structures', memcached_upper_bounds("Internal connection handles", 0, 0)),
            ('curr_connections', memcached_upper_bounds("Open Connections", 0, 0)),
            ('listen_disabled_num',
             memcached_upper_bounds("Connection fails due to connection limit", 5, 10)),
            ('conn_yields', memcached_upper_bounds("Forced connection yields", 1, 5)),
            ('decr_hits', memcached_upper_bounds("Number of succesful decr commands", 0, 0)),
            ('decr_misses', memcached_upper_bounds("Number of failed decr commands", 0, 0)),
            ('incr_hits', memcached_upper_bounds("Number of successful incr commands", 0, 0)),
            ('incr_misses', memcached_upper_bounds("Number of failed incr commands", 0, 0)),
            ('delete_hits', memcached_upper_bounds("Cache hits on delete", 0, 0)),
            ('delete_misses', memcached_upper_bounds("Cache misses on delete", 1000, 2000)),
            ('reclaimed',
             memcached_upper_bounds("Number of times a request used memory from an expired key", 0,
                                    0))
        ]),
    TextInput(title=_("Instance")),
    match_type='dict',
)
