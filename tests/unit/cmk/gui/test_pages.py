#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

import sys
from typing import override

import pytest
from werkzeug.test import create_environ

import cmk.gui.pages
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.pages import Page, PageContext, PageEndpoint
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions


@pytest.mark.usefixtures("monkeypatch")
def test_page_registry_register_page(capsys: pytest.CaptureFixture[str]) -> None:
    page_registry = cmk.gui.pages.PageRegistry()

    class PageClass(cmk.gui.pages.Page):
        @override
        def page(self, ctx: PageContext) -> None:
            sys.stdout.write("234")

    page_registry.register(PageEndpoint("234handler", PageClass()))

    endpoint = page_registry.get("234handler")
    assert isinstance(endpoint, PageEndpoint)
    handler = endpoint.handler
    assert isinstance(handler, Page)

    handler.handle_page(
        PageContext(
            config=Config(),
            request=Request(create_environ()),
            transactions=transactions,
            session=session,
        )
    )
    assert capsys.readouterr()[0] == "234"


@pytest.mark.usefixtures("monkeypatch")
def test_page_registry_register_page_handler(capsys: pytest.CaptureFixture[str]) -> None:
    page_registry = cmk.gui.pages.PageRegistry()

    def page(ctx: PageContext) -> None:
        sys.stdout.write("234")

    page_registry.register(PageEndpoint("234handler", page))

    endpoint = page_registry.get("234handler")
    assert isinstance(endpoint, PageEndpoint)
    handler = endpoint.handler
    assert not isinstance(handler, Page)

    handler(
        PageContext(
            config=Config(),
            request=Request(create_environ()),
            transactions=transactions,
            session=session,
        )
    )
    assert capsys.readouterr()[0] == "234"


def test_get_page_handler_default() -> None:
    def dummy(ctx: PageContext) -> None:
        pass

    handler = cmk.gui.pages.get_page_handler("123handler", dummy)
    assert handler is dummy
