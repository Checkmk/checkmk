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
#include <iterator>
#include <string>
#include <utility>
#include <vector>

#include "Column.h"
#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "Row.h"
#ifdef CMC
#include "contact_fwd.h"
#else
#include "nagios.h"
#endif
class RowRenderer;

#ifdef CMC
class Object;
#endif

class CommentColumn : public ListColumn {
public:
    enum class verbosity { none, medium, full };
    template <class T>
    class Callback;
    CommentColumn(const std::string &name, const std::string &description,
                  ColumnOffsets offsets, verbosity v)
        : ListColumn{name, description, std::move(offsets)}, _verbosity{v} {}
    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

private:
    verbosity _verbosity;
    [[nodiscard]] virtual std::vector<CommentData> getEntries(
        Row row) const = 0;
};

template <class T>
class CommentColumn::Callback : public CommentColumn {
public:
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets, CommentColumn::verbosity v,
             MonitoringCore *mc)
        : CommentColumn{name, description, offsets, v}, _mc{mc} {}

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;

    [[nodiscard]] std::vector<CommentData> getEntries(Row row) const override;
    [[nodiscard]] std::vector<CommentData> comments(const void *data) const;
};

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
template <class T>
std::vector<std::string> CommentColumn::Callback<T>::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) { return std::to_string(entry._id); });
    return values;
}

template <class T>
std::vector<CommentData> CommentColumn::Callback<T>::getEntries(Row row) const {
    if (const auto *const data = columnData<void>(row)) {
        return comments(data);
    }
    return {};
}

#ifdef CMC
template <>
inline std::vector<CommentData> CommentColumn::Callback<Object>::comments(
    const void *const data) const {
    return _mc->comments(reinterpret_cast<const MonitoringCore::Host *>(data));
}
#else
template <>
inline std::vector<CommentData> CommentColumn::Callback<host>::comments(
    const void *const data) const {
    return _mc->comments(reinterpret_cast<const MonitoringCore::Host *>(data));
}

template <>
inline std::vector<CommentData> CommentColumn::Callback<service>::comments(
    const void *const data) const {
    return _mc->comments(
        reinterpret_cast<const MonitoringCore::Service *>(data));
}
#endif
#endif  // CommentColumn_h
