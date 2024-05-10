// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableCrashReports.h"

#include <filesystem>
#include <functional>
#include <memory>

#include "livestatus/Column.h"
#include "livestatus/CrashReport.h"
#include "livestatus/DynamicColumn.h"
#include "livestatus/DynamicFileColumn.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"

using row_type = CrashReport;

TableCrashReports::TableCrashReports(ICore *mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<row_type>>(
        "id", "The ID of a crash report", offsets,
        [](const row_type &row) { return row.id; }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "component", "The component that crashed (gui, agent, check, etc.)",
        offsets, [](const row_type &row) { return row.component; }));
    addDynamicColumn(std::make_unique<DynamicFileColumn<row_type>>(
        "file", "Files related to the crash report (crash.info, etc.)", offsets,
        [mc](const row_type & /*row*/) {
            return mc->paths()->crash_reports_directory();
        },
        [](const std::string &args) { return std::filesystem::path{args}; }));
}

std::string TableCrashReports::name() const { return "crashreports"; }

std::string TableCrashReports::namePrefix() const { return "crashreport_"; }

void TableCrashReports::answerQuery(Query &query, const User & /*user*/,
                                    const ICore &core) {
    mk::crash_report::any(core.paths()->crash_reports_directory(),
                          [&query](const row_type &row) {
                              return !query.processDataset(Row{&row});
                          });
}
