#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

import pytest


@pytest.fixture(name="notify_context")
def fixture_notify_context(monkeypatch: pytest.MonkeyPatch) -> Callable[[Mapping[str, str]], None]:
    def set_context(context: Mapping[str, str]) -> None:
        for key, value in context.items():
            monkeypatch.setenv(f"NOTIFY_{key}", value)

    return set_context


def exit_code(main: Callable[[], object]) -> int | str | None:
    with pytest.raises(SystemExit) as exc:
        main()
    return exc.value.code


def explicit_password(parameter: str, secret: str) -> dict[str, str]:
    """An explicit password as cmk.base.events flattens it into the notification context."""
    return {
        f"{parameter}_1": "cmk_postprocessed",
        f"{parameter}_2": "explicit_password",
        f"{parameter}_3": f"uuid1234\t{secret}",
        f"{parameter}_3_1": "uuid1234",
        f"{parameter}_3_2": secret,
    }
