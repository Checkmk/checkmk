#include "TableCrashReports.h"
#include <memory>
#include <string>
#include "Column.h"
#include "CrashReport.h"
#include "DynamicColumn.h"
#include "DynamicHostFileColumn.h"
#include "MonitoringCore.h"
#include "OffsetSStringColumn.h"
#include "Query.h"
#include "Row.h"

TableCrashReports::TableCrashReports(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<OffsetSStringColumn>(
        "id", "The ID of a crash report", -1, -1, -1,
        DANGEROUS_OFFSETOF(CrashReport, _id)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "component", "The component that crashed (gui, agent, check, etc.)", -1,
        -1, -1, DANGEROUS_OFFSETOF(CrashReport, _component)));
    addDynamicColumn(std::make_unique<DynamicHostFileColumn>(
        "file", "Files related to the crash report (crash.info, etc.)", -1, -1,
        -1, [mc] { return mc->crashReportPath(); }));
}

std::string TableCrashReports::name() const { return "crashreports"; }

std::string TableCrashReports::namePrefix() const { return "crashreport_"; }

void TableCrashReports::answerQuery(Query *query) {
    mk::crash_report::any(core()->crashReportPath(),
                          [&query](const CrashReport &cr) {
                              return !query->processDataset(Row(&cr));
                          });
}
