#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast


class ImportedNames:
    """Resolves names bound by a file's absolute imports to their qualified names.

    Relative imports and names rebound by assignment are not tracked.
    """

    def __init__(self) -> None:
        self._names: dict[str, str] = {}

    def record(self, node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname is None:
                    # `import logging.config` binds the top-level package name.
                    top_level = alias.name.partition(".")[0]
                    self._names[top_level] = top_level
                else:
                    self._names[alias.asname] = alias.name
        elif node.level == 0 and node.module is not None:
            for alias in node.names:
                self._names[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def qualified_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return self._names.get(node.id)
        if isinstance(node, ast.Attribute) and (base := self.qualified_name(node.value)):
            return f"{base}.{node.attr}"
        return None
