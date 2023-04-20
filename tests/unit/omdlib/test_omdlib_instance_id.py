#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID

from omdlib.contexts import SiteContext
from omdlib.instance_id import has_instance_id, save_instance_id


def test_save_instance_id(site_context: SiteContext) -> None:
    assert not has_instance_id(site_context)

    save_instance_id(site_context)

    assert has_instance_id(site_context)

    instance_id_filepath = Path(site_context.dir, "etc/omd/instance_id")
    with instance_id_filepath.open("r", encoding="utf-8") as fp:
        UUID(fp.read())


def test_save_instance_id_twice(site_context: SiteContext) -> None:
    assert not has_instance_id(site_context)

    save_instance_id(site_context)

    assert has_instance_id(site_context)

    instance_id_filepath = Path(site_context.dir, "etc/omd/instance_id")
    with instance_id_filepath.open("r", encoding="utf-8") as fp:
        instance_id = UUID(fp.read())

    save_instance_id(site_context)

    assert has_instance_id(site_context)

    with instance_id_filepath.open("r", encoding="utf-8") as fp:
        assert UUID(fp.read()) != instance_id
