// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CommentColumn.h"

#include "Renderer.h"

void CommentColumn::output(Row row, RowRenderer &r,
                           const contact * /*auth_user*/,
                           std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &comment : getEntries(row)) {
        switch (_verbosity) {
            case verbosity::none:
                l.output(comment._id);
                break;
            case verbosity::info: {
                SublistRenderer s(l);
                s.output(comment._id);
                s.output(comment._author);
                s.output(comment._comment);
                break;
            }
            case verbosity::extra_info: {
                SublistRenderer s(l);
                s.output(comment._id);
                s.output(comment._author);
                s.output(comment._comment);
                s.output(comment._entry_type);
                s.output(comment._entry_time);
                break;
            }
        }
    }
}
