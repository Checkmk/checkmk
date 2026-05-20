#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Protocol

from cmk.rulesets.v1.form_specs import FormSpec


class FormSpecAdapter[Model, F: FormSpec[Any]](Protocol):
    """Adapter between a strongly-typed model and its form UI representation.

    Implement this protocol when the shape a form spec works with differs
    from the model used in the rest of the code base (and stored on disk).
    The conversion then happens explicitly at the form boundary: call
    ``to_form_spec`` before rendering and ``from_form_spec`` after parsing,
    keeping the model untouched everywhere else.

    ``data``/``to_form_spec`` use ``object`` because the form-world value
    depends on the form spec (e.g. a cascading choice yields a tagged tuple,
    a dictionary yields a dict); implementations narrow as needed.
    """

    def form_spec(self) -> F: ...

    def from_form_spec(self, data: object) -> Model: ...

    def to_form_spec(self, model: Model) -> object: ...
