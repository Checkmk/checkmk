#ifndef TableCrashReports_h
#define TableCrashReports_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Table.h"

class MonitoringCore;
class Query;

class TableCrashReports : public Table {
public:
    explicit TableCrashReports(MonitoringCore *mc);
    [[nodiscard]] std::string name() const final;
    [[nodiscard]] std::string namePrefix() const final;
    void answerQuery(Query *) final;
};

#endif  // TableCrashReports_h
