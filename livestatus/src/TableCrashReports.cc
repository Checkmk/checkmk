// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableCrashReports.h"

#include <filesystem>
#include <memory>

#include "Column.h"
#include "CrashReport.h"
#include "DynamicColumn.h"
#include "DynamicFileColumn.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"

TableCrashReports::TableCrashReports(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<CrashReport>>(
        "id", "The ID of a crash report", offsets,
        [](const CrashReport &r) { return r._id; }));
    addColumn(std::make_unique<StringColumn<CrashReport>>(
        "component", "The component that crashed (gui, agent, check, etc.)",
        offsets, [](const CrashReport &r) { return r._component; }));
    addDynamicColumn(std::make_unique<DynamicFileColumn<CrashReport>>(
        "file", "Files related to the crash report (crash.info, etc.)", offsets,
        [mc] { return mc->crashReportPath(); },
        [](const CrashReport & /*r*/, const std::string &args) {
            return std::filesystem::path{args};
        }));
}

std::string TableCrashReports::name() const { return "crashreports"; }

std::string TableCrashReports::namePrefix() const { return "crashreport_"; }

void TableCrashReports::answerQuery(Query &query, const User & /*user*/) {
    mk::crash_report::any(core()->crashReportPath(),
                          [&query](const CrashReport &cr) {
                              const CrashReport *r = &cr;
                              return !query.processDataset(Row{r});
                          });
}
