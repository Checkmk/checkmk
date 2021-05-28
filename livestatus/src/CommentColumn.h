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
class RowRenderer;
class ColumnOffsets;

namespace detail {
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
}  // namespace detail

class CommentColumn : public ListColumn {
public:
    using verbosity = detail::CommentRenderer::verbosity;
    using ListColumn::ListColumn;
    template <class T, class U>
    class Callback;

protected:
    template <class U>
    static std::string serialize(const U &);
};

template <class T, class U>
class CommentColumn::Callback : public CommentColumn {
    using function_type = std::function<std::vector<U>(const T &)>;

public:
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets, CommentColumn::verbosity v,
             const function_type &f)
        : CommentColumn{name, description, offsets}
        , renderer_{[this](Row row) { return this->getEntries(row); }, v}
        , f_{f} {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    friend class detail::CommentRenderer;
    detail::CommentRenderer renderer_;
    const function_type f_;

    [[nodiscard]] std::vector<U> getEntries(Row row) const {
        const T *data = columnData<T>(row);
        return data == nullptr ? std::vector<U>{} : f_(*data);
    }
};

template <class T, class U>
void CommentColumn::Callback<T, U>::output(
    Row row, RowRenderer &r, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    renderer_(row, r);
}

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
template <class T, class U>
std::vector<std::string> CommentColumn::Callback<T, U>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   serialize<U>);
    return values;
}

template <>
inline std::string CommentColumn::serialize(const CommentData &entry) {
    return std::to_string(entry._id);
}

#endif
