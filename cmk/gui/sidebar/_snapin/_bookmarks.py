#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Self, TypedDict

from cmk.ccc.user import UserId

from cmk.utils.urls import is_allowed_url

from cmk.gui import pagetypes
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.valuespec import (
    Alternative,
    FixedValue,
    IconSelector,
    ListOf,
    OptionalDropdownChoice,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)

from ._base import SidebarSnapin
from ._helpers import begin_footnote_links, end_footnote_links, iconlink, link


class BookmarkSpec(TypedDict):
    title: str
    url: str
    icon: None | str
    topic: None | str


class BookmarkListModel(pagetypes.OverridableModel):
    default_topic: str
    bookmarks: list[BookmarkSpec]


@dataclass(kw_only=True)
class BookmarkListConfig(pagetypes.OverridableConfig):
    default_topic: str
    bookmarks: list[BookmarkSpec]


class BookmarkList(pagetypes.Overridable[BookmarkListConfig]):
    @classmethod
    def deserialize(cls, page_dict: Mapping[str, object]) -> Self:
        deserialized = BookmarkListModel.model_validate(page_dict)
        return cls(
            BookmarkListConfig(
                name=deserialized.name,
                title=deserialized.title,
                description=deserialized.description,
                owner=deserialized.owner,
                public=deserialized.public,
                hidden=deserialized.hidden,
                default_topic=deserialized.default_topic,
                bookmarks=deserialized.bookmarks,
            )
        )

    def serialize(self) -> dict[str, object]:
        return BookmarkListModel(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            owner=self.config.owner,
            public=self.config.public,
            hidden=self.config.hidden,
            default_topic=self.config.default_topic,
            bookmarks=self.config.bookmarks,
        ).model_dump()

    @classmethod
    def type_name(cls) -> str:
        return "bookmark_list"

    @classmethod
    def type_icon(cls) -> str:
        return "bookmark_list"

    @classmethod
    def phrase(cls, phrase: pagetypes.PagetypePhrase) -> str:
        return {
            "title": _("Bookmark list"),
            "title_plural": _("Bookmark lists"),
            "add_to": _("Add to bookmark list"),
            "clone": _("Clone bookmark list"),
            "create": _("Create bookmark list"),
            "edit": _("Edit bookmark list"),
            "new": _("Add list"),
        }.get(phrase, pagetypes.Base.phrase(phrase))

    @classmethod
    def parameters(
        cls, mode: pagetypes.PageMode
    ) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        def bookmark_config_to_vs(v):
            if v:
                return (v["title"], v["url"], v["icon"], v["topic"])
            return v

        def bookmark_vs_to_config(v):
            return {
                "title": v[0],
                "url": v[1],
                "icon": v[2],
                "topic": v[3],
            }

        parameters = super().parameters(mode)

        parameters += [
            (
                _("Bookmarks"),
                [
                    # sort-index, key, valuespec
                    (
                        2.5,
                        "default_topic",
                        TextInput(
                            title=_("Default topic") + "<sup>*</sup>",
                            size=50,
                            allow_empty=False,
                        ),
                    ),
                    (
                        3.0,
                        "bookmarks",
                        ListOf(
                            # For the editor we want a compact dialog. The tuple horizontal editin mechanism
                            # is exactly the thing we want. But we want to store the data as dict. This is a
                            # nasty hack to use the transform by default. Better would be to make Dict render
                            # the same way the tuple is rendered.
                            title=_("Bookmarks"),
                            add_label=_("Add bookmark"),
                            valuespec=Transform(
                                valuespec=Tuple(
                                    elements=[
                                        (
                                            TextInput(
                                                title=_("Title") + "<sup>*</sup>",
                                                size=30,
                                                allow_empty=False,
                                            )
                                        ),
                                        (
                                            TextInput(
                                                title=_("URL"),
                                                size=50,
                                                allow_empty=False,
                                                validate=cls.validate_url,
                                            )
                                        ),
                                        (IconSelector(title=_("Icon"), with_emblem=False)),
                                        (cls._vs_topic()),
                                    ],
                                    orientation="horizontal",
                                    title=_("Bookmarks"),
                                ),
                                to_valuespec=bookmark_config_to_vs,
                                from_valuespec=bookmark_vs_to_config,
                            ),
                        ),
                    ),
                ],
            )
        ]

        return parameters

    @classmethod
    def _vs_topic(cls) -> Alternative:
        choices = cls._topic_choices()

        return Alternative(
            elements=[
                FixedValue(
                    value=None,
                    title=_("Use default topic"),
                    totext="",
                ),
                OptionalDropdownChoice(
                    title=_("Individual topic"),
                    choices=choices,
                    default_value=choices[0][0] if choices else "",
                    explicit=TextInput(
                        size=30,
                        allow_empty=False,
                    ),
                    otherlabel="%s" % _("Add new topic"),
                ),
            ],
            title=_("Topic") + "<sup>*</sup>",
            orientation="horizontal",
        )

    @classmethod
    def _topic_choices(cls) -> list[tuple[str, str]]:
        topics = set()
        instances = BookmarkList.load()
        for instance in instances.instances_sorted():
            if instance.is_permitted():
                for topic, _bookmarks in instance.bookmarks_by_topic():
                    if topic is None:
                        topic = instance.default_bookmark_topic()
                    topics.add(topic)
        return [(t, t) for t in sorted(list(topics))]

    @classmethod
    def validate_url(cls, value: str, varprefix: str) -> None:
        if is_allowed_url(value, cross_domain=True, schemes=["http", "https"]):
            return
        raise MKUserError(varprefix, _("This URL ist not allowed to be used as bookmark"))

    @classmethod
    def add_default_bookmark_list(
        cls,
        instances: pagetypes.OverridableInstances[BookmarkList],
        user_id: UserId,
    ) -> None:
        instances.add_instance(
            (user_id, "my_bookmarks"),
            cls(
                BookmarkListConfig(
                    name="my_bookmarks",
                    title="My Bookmarks",
                    public=False,
                    owner=user_id,
                    description="Your personal bookmarks",
                    default_topic="My Bookmarks",
                    bookmarks=[],
                )
            ),
        )

    @classmethod
    def new_bookmark(cls, title: str, url: str) -> BookmarkSpec:
        return {
            "title": title,
            "url": url,
            "icon": None,
            "topic": None,
        }

    def default_bookmark_topic(self) -> str:
        return self.config.default_topic

    def bookmarks_by_topic(self) -> list[tuple[str, list[BookmarkSpec]]]:
        topics: dict[str, list[BookmarkSpec]] = {}
        default_topic = self.default_bookmark_topic()
        for bookmark in self.config.bookmarks:
            topic = topics.setdefault(bookmark["topic"] or default_topic, [])
            topic.append(bookmark)
        return sorted(topics.items())

    def add_bookmark(self, title: str, url: str) -> None:
        self.config.bookmarks.append(BookmarkList.new_bookmark(title, url))


class Bookmarks(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "bookmarks"

    @classmethod
    def title(cls) -> str:
        return _("Bookmarks")

    @classmethod
    def description(cls) -> str:
        return _(
            "A simple and yet practical snap-in allowing to create "
            "bookmarks to views and other content in the main frame"
        )

    def show(self, config: Config) -> None:
        for topic, bookmarks in self._get_bookmarks_by_topic():
            with foldable_container(
                treename="bookmarks",
                id_=topic,
                isopen=False,
                title=topic,
                indent=False,
            ):
                for bookmark in bookmarks:
                    icon = bookmark["icon"]
                    if not icon:
                        icon = "bookmark_list"

                    iconlink(bookmark["title"], bookmark["url"], icon)

        begin_footnote_links()
        link(
            _("Add bookmark"),
            "javascript:void(0)",
            onclick="cmk.sidebar.add_bookmark()",
        )
        link(_("Edit"), "bookmark_lists.py")
        end_footnote_links()

    def _get_bookmarks_by_topic(self):
        topics: dict[Any, list[Any]] = {}
        instances = BookmarkList.load()
        for instance in instances.instances_sorted():
            if instance.is_permitted():
                for topic, bookmarks in instance.bookmarks_by_topic():
                    if topic is None:
                        topic = instance.default_bookmark_topic()
                    bookmark_list = topics.setdefault(topic, [])
                    bookmark_list += bookmarks
        return sorted(topics.items())

    def _ajax_add_bookmark(self, config: Config) -> None:
        check_csrf_token()
        title = request.var("title")
        url = request.var("url")
        if title and url:
            BookmarkList.validate_url(url, "url")
            self._add_bookmark(title, url)
        self.show(config)

    def _add_bookmark(self, title: str, url: str) -> None:
        assert user.id is not None
        instances = BookmarkList.load()

        if not instances.has_instance((user.id, "my_bookmarks")):
            BookmarkList.add_default_bookmark_list(instances, user.ident)

        bookmarks = instances.instance((user.id, "my_bookmarks"))
        bookmarks.add_bookmark(title, self._try_shorten_url(url))
        BookmarkList.save_user_instances(instances)

    def _try_shorten_url(self, url: str) -> str:
        referer = request.referer
        if referer:
            ref_p = urllib.parse.urlsplit(referer)
            url_p = urllib.parse.urlsplit(url)

            # If http/https or user, pw, host, port differ, don't try to shorten
            # the URL to be linked. Simply use the full URI
            if ref_p.scheme == url_p.scheme and ref_p.netloc == url_p.netloc:
                # We try to remove http://hostname/some/path/check_mk from the
                # URI. That keeps the configuration files (bookmarks) portable.
                # Problem here: We have not access to our own URL, only to the
                # path part. The trick: we use the Referrer-field from our
                # request. That points to the sidebar.
                referer = ref_p.path
                url = url_p.path
                if url_p.query:
                    url += "?" + url_p.query
                removed = 0
                while "/" in referer and referer.split("/")[0] == url.split("/")[0]:
                    referer = referer.split("/", 1)[1]
                    url = url.split("/", 1)[1]
                    removed += 1

                if removed == 1:
                    # removed only the first "/". This should be an absolute path.
                    url = "/" + url
                elif "/" in referer:
                    # there is at least one other directory layer in the path, make
                    # the link relative to the sidebar.py's topdir. e.g. for pnp
                    # links in OMD setups
                    url = "../" + url
        return url

    def page_handlers(self) -> dict[str, Callable[[Config], None]]:
        return {
            "add_bookmark": self._ajax_add_bookmark,
        }
