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
#include "Column.h"
#include "StringColumn.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class MacroExpander {
public:
    virtual ~MacroExpander() = default;
    virtual std::optional<std::string> expand(const std::string &str) = 0;
    static std::optional<std::string> from_ptr(const char *str);
};

// poor man's monad...
class CompoundMacroExpander : public MacroExpander {
public:
    CompoundMacroExpander(std::unique_ptr<MacroExpander> first,
                          std::unique_ptr<MacroExpander> second);

    std::optional<std::string> expand(const std::string &str) override;

private:
    std::unique_ptr<MacroExpander> _first;
    std::unique_ptr<MacroExpander> _second;
};

class UserMacroExpander : public MacroExpander {
public:
    std::optional<std::string> expand(const std::string &str) override;
};

class CustomVariableExpander : public MacroExpander {
public:
    CustomVariableExpander(std::string prefix, const customvariablesmember *cvm,
                           const MonitoringCore *mc);

    std::optional<std::string> expand(const std::string &str) override;

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
                            const Column::Offsets &offsets,
                            const MonitoringCore *mc, int offset)
        : StringColumn(name, description, offsets)
        , _mc(mc)
        , _string_offset(offset) {}

    [[nodiscard]] std::string getValue(Row row) const override;

    [[nodiscard]] virtual std::unique_ptr<MacroExpander> getMacroExpander(
        Row row) const = 0;

protected:
    const MonitoringCore *const _mc;

private:
    const int _string_offset;
};

#endif  // OffsetStringMacroColumn_h
