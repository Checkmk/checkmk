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
#include <iterator>
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

#ifdef CMC
class Object;
#endif

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

struct DowntimeColumn : ListColumn {
    using ListColumn::ListColumn;
    template <class T, class U>
    class Callback;
};

template <class T, class U>
class DowntimeColumn::Callback : public DowntimeColumn {
    using function_type = std::function<std::vector<U>(const T &)>;

public:
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets, DowntimeRenderer::verbosity v,
             const function_type &f)
        : DowntimeColumn{name, description, offsets}
        , renderer_{[this](Row row) { return this->getEntries(row); }, v}
        , f_{f} {}

    void output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        renderer_(row, r);
    }

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    friend class DowntimeRenderer;
    DowntimeRenderer renderer_;
    const function_type f_;

    [[nodiscard]] std::vector<DowntimeData> getEntries(Row row) const;
    //[[nodiscard]] std::vector<DowntimeData> downtimes(const void *data) const;
};

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
template <class T, class U>
std::vector<std::string> DowntimeColumn::Callback<T, U>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   detail::column::serialize<U>);
    return values;
}

template <class T, class U>
std::vector<DowntimeData> DowntimeColumn::Callback<T, U>::getEntries(
    Row row) const {
    const T *data = columnData<T>(row);
    return data == nullptr ? std::vector<U>{} : f_(*data);
}

template <>
inline std::string detail::column::serialize(const DowntimeData &data) {
    return std::to_string(data._id);
}
#endif  // DowntimeColumn_h
