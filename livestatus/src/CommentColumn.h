// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CommentColumn_h
#define CommentColumn_h

#include "config.h"  // IWYU pragma: keep

// We use `std::transform` but IWYU does not want the header.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <functional>
#include <string>
#include <vector>

#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "Row.h"
#ifdef CMC
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif
class RowRenderer;
class ColumnOffsets;

class CommentRenderer {
    using function_type = std::function<std::vector<CommentData>(Row)>;

public:
    enum class verbosity { none, medium, full };
    CommentRenderer(const function_type &f, verbosity v)
        : f_{f}, verbosity_{v} {}
    void operator()(Row row, RowRenderer &r) const;

private:
    function_type f_;
    verbosity verbosity_;
};

template <class T, class U>
class CommentColumn : public ListColumn::Callback<T, U> {
public:
    CommentColumn(const std::string &name, const std::string &description,
                  const ColumnOffsets &offsets, CommentRenderer::verbosity v,
                  const typename ListColumn::Callback<T, U>::function_type &f)
        : ListColumn::Callback<T, U>{name, description, offsets, f}
        , renderer_{[this](Row row) { return this->getEntries(row); }, v} {}

    void output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        renderer_(row, r);
    }

private:
    friend class CommentRenderer;
    CommentRenderer renderer_;
};

template <>
inline std::string detail::column::serialize(const CommentData &data) {
    return std::to_string(data._id);
}

#endif
