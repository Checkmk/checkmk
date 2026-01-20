#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import itertools
from typing import NamedTuple

from jinja2 import Environment, PackageLoader, select_autoescape, StrictUndefined

from cmk.utils.version import RType, Version

from cmk.werks.models import Class, Compatibility, Edition, Werk, WerkV3

from .. import has_content, load_raw_files
from ..werk import sort_by_version_and_component, WerkTranslator


class SimpleWerk(NamedTuple):
    id: int
    title: str
    has_content: bool
    compatible: bool
    prefix: str
    url: str

    @classmethod
    def from_werk(cls, werk: Werk | WerkV3) -> "SimpleWerk":
        prefix = ""
        if werk.class_ == Class.FIX:
            prefix = "FIX: "
        elif werk.class_ == Class.SECURITY:
            prefix = "SEC: "

        return cls(
            id=werk.id,
            title=werk.title,
            has_content=has_content(werk.description),
            compatible=werk.compatible == Compatibility.COMPATIBLE,
            prefix=prefix,
            url=f"https://checkmk.com/werk/{werk.id}",
        )


class WerksByComponent(NamedTuple):
    component: str
    werks: list[SimpleWerk]


class WerksByEdition(NamedTuple):
    werks: list[WerksByComponent]
    len: int


def get_werks_by_edition(werks: list[Werk | WerkV3], edition: Edition) -> WerksByEdition:
    werks_by_edition = [werk for werk in werks if werk.edition == edition]
    result = []
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks_by_edition)
    for component, component_group in itertools.groupby(werklist, key=translator.component_of):
        result.append(
            WerksByComponent(
                component=component,
                werks=list(SimpleWerk.from_werk(w) for w in component_group),
            )
        )
    return WerksByEdition(werks=result, len=len(werks_by_edition))


def main(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)
    version_werks = [werk for werk in werks_list if werk.version == args.version]

    werks = {}
    for edition in [Edition.CRE, Edition.CEE, Edition.CCE, Edition.CME, Edition.CSE]:
        werks[edition.value] = get_werks_by_edition(version_werks, edition)

    env = Environment(
        loader=PackageLoader("cmk.utils.werks.announce", "templates"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )

    version = Version.from_str(args.version)
    feedback_mail = None

    if version.release.r_type == RType.b:
        release_type = "beta"
        assert (
            version.base is not None
        ), f"Expected version.base to be not None for release type beta: {version}"
        feedback_mail = f"feedback-{version.base.major}.{version.base.minor}-beta@checkmk.com"
    elif version.release.r_type == RType.p or version.release.is_unspecified():
        release_type = "stable"
    elif version.release.r_type == RType.daily:
        release_type = "daily"
    else:
        raise NotImplementedError(f"Can not create announcement for {version.release.r_type}")

    template = env.get_template(f"announce.{args.format}.jinja2")
    print(
        template.render(
            werks=werks,
            release_type=release_type,
            version=args.version,
            feedback_mail=feedback_mail,
        )
    )
