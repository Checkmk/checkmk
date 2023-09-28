#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths


def paint_wiki_notes(row):
    host = row["host_name"]
    svc = row.get("service_description")
    svc = svc.replace(":", "")
    svc = svc.replace("/", "")
    svc = svc.replace("\\", "")
    svc = svc.replace(" ", "_")
    svc = svc.lower()
    host = host.lower()
    filename = cmk.utils.paths.omd_root + "/var/dokuwiki/data/pages/docu/{}/{}.txt".format(
        host, svc
    )
    if not os.path.isfile(filename):
        filename = cmk.utils.paths.omd_root + "/var/dokuwiki/data/pages/docu/default/{}.txt".format(
            svc
        )

    text = "<a href='../wiki/doku.php?id=docu:default:%s'>Edit Default Instructions</a> - " % svc
    text += "<a href='../wiki/doku.php?id=docu:{}:{}'>Edit Host Instructions</a> <hr> ".format(
        host, svc
    )

    try:
        from pathlib import Path

        with Path(filename).open(encoding="utf-8") as fp:
            text += fp.read()
    except OSError:
        text += "No instructions found in " + filename

    return "", text + "<br /><br />"


multisite_painters["svc_wiki_notes"] = {
    "title": _("Instructions"),
    "short": _("Instr"),
    "columns": ["host_name", "service_description"],
    "paint": paint_wiki_notes,
}
