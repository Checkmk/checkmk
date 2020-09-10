// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CommentColumn_h
#define CommentColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>
#include <utility>
#include <vector>

#include "Column.h"
#include "ListColumn.h"
#include "contact_fwd.h"
struct CommentData;
class MonitoringCore;
class RowRenderer;
class Row;

class CommentColumn : public ListColumn {
public:
    CommentColumn(const std::string &name, const std::string &description,
                  ColumnOffsets offsets, MonitoringCore *mc, bool is_service,
                  bool with_info, bool with_extra_info)
        : ListColumn(name, description, std::move(offsets))
        , _mc(mc)
        , _is_service(is_service)
        , _with_info(with_info)
        , _with_extra_info(with_extra_info) {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;
    bool _is_service;
    bool _with_info;
    bool _with_extra_info;

    [[nodiscard]] std::vector<CommentData> comments_for_row(Row row) const;
};

#endif  // CommentColumn_h
