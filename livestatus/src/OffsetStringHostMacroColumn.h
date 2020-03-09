// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OffsetStringHostMacroColumn_h
#define OffsetStringHostMacroColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <optional>
#include <string>
#include "OffsetStringMacroColumn.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class HostMacroExpander : public MacroExpander {
public:
    HostMacroExpander(const host *hst, const MonitoringCore *mc);
    std::optional<std::string> expand(const std::string &str) override;

private:
    const host *_hst;
    CustomVariableExpander _cve;
};

class OffsetStringHostMacroColumn : public OffsetStringMacroColumn {
public:
    using OffsetStringMacroColumn::OffsetStringMacroColumn;

    [[nodiscard]] std::unique_ptr<MacroExpander> getMacroExpander(
        Row row) const override;
};

#endif  // OffsetStringHostMacroColumn_h
