// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimeColumn_h
#define DowntimeColumn_h

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
class ColumnOffsets;
class RowRenderer;

class DowntimeRenderer {
    using function_type = std::function<std::vector<DowntimeData>(Row)>;

public:
    enum class verbosity { none, medium, full };
    DowntimeRenderer(const function_type &f, verbosity v)
        : f_{f}, verbosity_{v} {}
    void operator()(Row row, RowRenderer &r) const;

private:
    function_type f_;
    verbosity verbosity_;
};

template <class T, class U>
class DowntimeColumn : public ListColumn::Callback<T, U> {
public:
    DowntimeColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets, DowntimeRenderer::verbosity v,
                   const typename ListColumn::Callback<T, U>::function_type &f)
        : ListColumn::Callback<T, U>{name, description, offsets, f}
        , renderer_{[this](Row row) { return this->getEntries(row); }, v} {}

    void output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        renderer_(row, r);
    }

private:
    friend class DowntimeRenderer;
    DowntimeRenderer renderer_;
};

template <>
inline std::string detail::column::serialize(const DowntimeData &data) {
    return std::to_string(data._id);
}
#endif  // DowntimeColumn_h
