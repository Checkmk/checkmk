#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.product_usage.collectors.user_store import load_users
from cmk.product_usage.schema import UserCount

_FREE_MAIL_DOMAINS = frozenset(
    {
        "126.com",
        "163.com",
        "aim.com",
        "aol.com",
        "arcor.de",
        "att.net",
        "bk.ru",
        "bluewin.ch",
        "btinternet.com",
        "centrum.cz",
        "comcast.net",
        "daum.net",
        "fastmail.com",
        "foxmail.com",
        "free.fr",
        "freenet.de",
        "gmail.com",
        "gmx.at",
        "gmx.ch",
        "gmx.com",
        "gmx.de",
        "gmx.fr",
        "gmx.net",
        "googlemail.com",
        "hey.com",
        "hotmail.co.uk",
        "hotmail.com",
        "hotmail.de",
        "hotmail.es",
        "hotmail.fr",
        "hotmail.it",
        "icloud.com",
        "inbox.ru",
        "interia.pl",
        "kpnmail.nl",
        "laposte.net",
        "libero.it",
        "list.ru",
        "live.be",
        "live.co.uk",
        "live.com",
        "live.de",
        "live.fr",
        "live.it",
        "live.nl",
        "mac.com",
        "mail.com",
        "mail.ru",
        "mailbox.org",
        "me.com",
        "msn.com",
        "naver.com",
        "o2.pl",
        "onet.pl",
        "online.de",
        "orange.fr",
        "outlook.com",
        "outlook.de",
        "outlook.es",
        "outlook.fr",
        "outlook.it",
        "pm.me",
        "posteo.de",
        "proton.me",
        "protonmail.ch",
        "protonmail.com",
        "qq.com",
        "rediffmail.com",
        "rocketmail.com",
        "sbcglobal.net",
        "seznam.cz",
        "sfr.fr",
        "sina.com",
        "sky.com",
        "t-online.de",
        "telenet.be",
        "tiscali.it",
        "tuta.io",
        "tutanota.com",
        "tutanota.de",
        "verizon.net",
        "virgilio.it",
        "virginmedia.com",
        "wanadoo.fr",
        "web.de",
        "wp.pl",
        "yahoo.ca",
        "yahoo.co.in",
        "yahoo.co.jp",
        "yahoo.co.uk",
        "yahoo.com",
        "yahoo.com.br",
        "yahoo.de",
        "yahoo.es",
        "yahoo.fr",
        "yahoo.it",
        "yandex.com",
        "yandex.ru",
        "ymail.com",
        "ziggo.nl",
        "zoho.com",
    }
)


def collect(default_config_dir: Path) -> UserCount:
    is_free_mail = [
        _is_free_mail(user_id)
        for user_id, user in load_users(default_config_dir).items()
        if user.get("connector") == "cognito"
    ]
    return UserCount(business=is_free_mail.count(False), non_business=is_free_mail.count(True))


def _is_free_mail(user_id: str) -> bool:
    # A Cognito user's ID is the email address it logs in with.
    labels = user_id.rpartition("@")[2].lower().split(".")
    return any(".".join(labels[i:]) in _FREE_MAIL_DOMAINS for i in range(len(labels)))
