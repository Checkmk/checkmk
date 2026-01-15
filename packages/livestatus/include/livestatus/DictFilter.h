// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DictFilter_h
#define DictFilter_h

#include <chrono>
#include <functional>
#include <string>
#include <unordered_map>

#include "Interface.h"
#include "livestatus/ColumnFilter.h"
#include "livestatus/Row.h"
#include "livestatus/StringFilter.h"

class Logger;
enum class RelationalOperator;

class DictStrValueFilter : public ColumnFilter {
    // Elsewhere, `function_type` is a std::variant of functions but we
    // currently have a single element, so we skip that entirely.
    using function_type = std::function<Attributes(Row)>;

public:
    DictStrValueFilter(Kind kind, std::string columnName, function_type f,
                       RelationalOperator relOp, const std::string &value);
    [[nodiscard]] bool accepts(
        Row row, const User &user,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;

private:
    function_type f_;
    StringFilter filter_;
};

class DictDoubleValueFilter : public ColumnFilter {
    // Elsewhere, `function_type` is a std::variant of functions but we
    // currently have a single element, so we skip that entirely.
    using function_type =
        std::function<std::unordered_map<std::string, double>(Row)>;

public:
    DictDoubleValueFilter(Kind kind, std::string columnName, function_type f,
                          RelationalOperator relOp, const std::string &value,
                          Logger *logger);
    [[nodiscard]] bool accepts(
        Row row, const User &user,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;
    [[nodiscard]] Logger *logger() const { return logger_; }

private:
    function_type f_;
    std::string ref_value_;
    std::string ref_varname_;
    Logger *logger_;
};

#endif  // DictFilter_h
