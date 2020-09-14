// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <optional>
#include <string>
#include <utility>

#include "Column.h"
#include "StringColumn.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class MacroExpander {
public:
    virtual ~MacroExpander() = default;
    [[nodiscard]] virtual std::optional<std::string> expand(
        const std::string &str) const = 0;
    static std::optional<std::string> from_ptr(const char *str);
};

// poor man's monad...
class CompoundMacroExpander : public MacroExpander {
public:
    CompoundMacroExpander(std::unique_ptr<MacroExpander> first,
                          std::unique_ptr<MacroExpander> second);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    std::unique_ptr<MacroExpander> _first;
    std::unique_ptr<MacroExpander> _second;
};

class UserMacroExpander : public MacroExpander {
public:
    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;
};

class CustomVariableExpander : public MacroExpander {
public:
    CustomVariableExpander(std::string prefix, const customvariablesmember *cvm,
                           const MonitoringCore *mc);

    [[nodiscard]] std::optional<std::string> expand(
        const std::string &str) const override;

private:
    std::string _prefix;
    const MonitoringCore *const _mc;
    const customvariablesmember *_cvm;
};

class OffsetStringMacroColumn : public StringColumn {
public:
    // TODO(ml): 5 offsets!
    OffsetStringMacroColumn(const std::string &name,
                            const std::string &description,
                            const ColumnOffsets &offsets,
                            const MonitoringCore *mc,
                            ColumnOffsets offsets_string)
        : StringColumn(name, description, offsets)
        , _mc(mc)
        , _offsets_string(std::move(offsets_string)) {}

    [[nodiscard]] std::string getValue(Row row) const override;

    [[nodiscard]] virtual std::unique_ptr<MacroExpander> getMacroExpander(
        Row row) const = 0;

protected:
    const MonitoringCore *const _mc;

private:
    ColumnOffsets _offsets_string;
};

#endif  // OffsetStringMacroColumn_h
