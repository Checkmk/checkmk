#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.config import Config
from cmk.gui.watolib._autocompleters import tag_group_opt_autocompleter
from cmk.ruleset_matcher.tags import get_effective_tag_config, TagConfigSpec


def test_tags_without_a_selected_group_offer_no_choices() -> None:
    config = Config(tags=get_effective_tag_config(TagConfigSpec(tag_groups=[], aux_tags=[])))

    assert tag_group_opt_autocompleter(config, "", {"strict": True}) == []
