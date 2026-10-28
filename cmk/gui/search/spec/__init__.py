#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Search spec of the global search

``parse(query)`` turns a global search query into a typed ``SearchSpec``. It has
no page or livestatus dependencies: turning the spec into page filters is up to the caller.

The prefixes are the ones of the legacy quicksearch (``cmk/gui/search/_engines/_livestatus.py``),
so that the dropdown suggestions and the pages a query opens agree on what users type. The
semantics are defined here and differ from the legacy quicksearch where noted below.

Syntax
    A prefix is one or two lower-case letters followed by ``:`` at the start of the query or after
    whitespace, e.g. ``h:``. Its value runs up to the next prefix, surrounding whitespace is
    stripped, so ``h:web server s:cpu`` has the values ``web server`` and ``cpu``. Line breaks
    and other control characters count as spaces. Anything else followed by ``:`` is part of the
    value, e.g. ``al:note: rack 4`` or ``C:drive``. So is the key at the start of a label or tag
    value, so ``hl: os:linux`` equals ``hl:os:linux``.

    =======  ===============  =======  ===============
    Prefix   Term             Prefix   Term
    =======  ===============  =======  ===============
    ``h:``   ``HostName``     ``s:``   ``ServiceName``
    ``al:``  ``HostAlias``    ``sg:``  ``ServiceGroup``
    ``ad:``  ``HostAddress``  ``st:``  ``ServiceState``
    ``hg:``  ``HostGroup``    ``sl:``  ``ServiceLabel``
    ``hl:``  ``HostLabel``    ``sf:``  ``ServiceFolder``
    ``tg:``  ``HostTag``
    ``hf:``  ``HostFolder``
    =======  ===============  =======  ===============

Combining
    * Terms with the same prefix are or-ed: ``h:web h:db`` finds hosts named web or db.
    * Except for tags and labels (``tg:``, ``hl:``, ``sl:``), which are and-ed to narrow down the
      search: ``tg:prod tg:linux`` finds hosts with both tags.
    * Terms with different prefixes are and-ed: ``h:web s:cpu`` finds the services matching cpu
      on hosts matching web. ``PrefixedSearch.clauses`` holds one clause per prefix (per term for
      tags and labels), in the order of first appearance.
    * A query without prefix becomes ``UnprefixedSearch``. It stands for what the global search
      dropdown searches without prefix (host name, alias and address, service name), apart from
      the monitor menu entries. Which of these fields a page filters on is up to the caller.

Matching
    * ``h:``, ``al:``, ``ad:``, ``s:`` and a query without prefix: the value is a regular
      expression that matches anywhere in the field (unanchored), case-insensitive. As in the
      dropdown, every ``*`` becomes ``.*``, so ``web*`` and ``*web`` work as globs.
      The pattern is checked like any other regex input in the GUI: it must compile in Python
      and must not use look-arounds. This is best effort: livestatus matches with re2, so a
      pattern only re2 rejects (e.g. a backreference) still fails in the query.
    * ``hf:``, ``sf:``: the value is a folder path, not a regular expression. It matches literally
      except for ``*``, which is a wildcard, and is case-insensitive. It matches the folders whose
      path starts with it, including their subfolders. Leading and trailing ``/`` are ignored.
    * ``hg:``, ``sg:``: a group name, matched exactly and case-sensitive, or a name prefix ending
      in ``*``: ``hg:linux*`` finds the hosts in a group whose name starts with ``linux``. Not a
      regular expression, as the pages filter groups by name. A ``*`` anywhere else is literal, a
      value that is just ``*`` is an error.
    * ``hl:``, ``sl:``: ``key:value``, split at the first ``:``, matched exactly (except for a
      trailing ``*``, see below) and case-sensitive. Whitespace around that ``:`` is ignored, also
      for ``tg:``, so ``hl:os : linux`` equals ``hl:os:linux``. Or just a key prefix ending in
      ``*``, which matches any value: ``hl:cmk/aws*`` finds the labels whose key starts with
      ``cmk/aws``.
    * ``tg:``: ``group:tag``, or just ``tag``, which matches the tag in any tag group. Tag IDs
      are only unique within their group, so the caller resolves a bare tag via the tag config,
      possibly to several groups. Matched exactly (except for a trailing ``*``, see below) and
      case-sensitive.
    * ``hl:``, ``sl:``, ``tg:``: a trailing ``*`` in the value or tag matches by prefix, so
      ``hl:os:lin*`` finds ``os:linux`` and ``tg:os:lin*`` finds the tags of group ``os``
      starting with ``lin``. A value or tag that is just ``*`` matches any value of exactly that
      key or any tag of exactly that group: ``hl:os:*``, ``tg:os:*``. It is kept as it is in the
      term, not turned into a regex. A ``*`` anywhere else is literal, ``hl:os:l*x`` matches the
      value ``l*x``. A key, tag group or tag without group that is just ``*`` is an error.
    * ``st:``: one of ``ok``, ``warn``, ``crit``, ``unkn``, ``pend``, case-insensitive. Several
      states can be given as ``warn|crit`` or ``(warn|crit)``, which equals ``st:warn st:crit``.

Errors (``SearchParseError``)
    An empty query, an unknown prefix, a prefix without value, text before the first prefix, an
    invalid regular expression and an invalid value for a prefix (label that is neither
    ``key:value`` nor a key prefix, a group, key, tag group or tag without group that is just
    ``*``, unknown service state, empty folder).

Errors (``UnsupportedSearchError``)
    Raised by the callers, not by ``parse``: a valid spec that the page it is routed to can't
    filter on, e.g. a service term on All hosts or a tag unknown to the tag config.

Differences to the legacy quicksearch
    * ``hg:`` and ``sg:`` match group names, not regular expressions. Alone, the legacy
      quicksearch matches them as a regular expression against the names of the groups, combined
      with other prefixes it matches them exactly, as here.
    * Any number of ``tg:`` terms is allowed, the legacy quicksearch allows at most three.
    * Nothing is dropped silently. The legacy quicksearch ignores text before the first prefix,
      unknown service states and empty folders, and treats an unknown prefix as part of the value.
    * A query without prefix does not follow the quicksearch search order (neither the
      ``quicksearch_search_order`` setting nor the unified search's fixed order). The order serves
      the dropdown, which fills several result groups, while the spec selects one page.
"""

from ._parse import parse, SearchParseError
from ._terms import (
    HostAddress,
    HostAlias,
    HostFolder,
    HostGroup,
    HostLabel,
    HostName,
    HostTag,
    PrefixedSearch,
    SearchSpec,
    ServiceFolder,
    ServiceGroup,
    ServiceLabel,
    ServiceName,
    ServiceState,
    ServiceStateName,
    Term,
    UnprefixedSearch,
    UnsupportedSearchError,
)

__all__ = [
    "HostAddress",
    "HostAlias",
    "HostFolder",
    "HostGroup",
    "HostLabel",
    "HostName",
    "HostTag",
    "parse",
    "PrefixedSearch",
    "SearchParseError",
    "SearchSpec",
    "ServiceFolder",
    "ServiceGroup",
    "ServiceLabel",
    "ServiceName",
    "ServiceState",
    "ServiceStateName",
    "Term",
    "UnprefixedSearch",
    "UnsupportedSearchError",
]
