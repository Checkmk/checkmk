#ifndef CrashReport_h
#define CrashReport_h

#include <string>

class TableCrashReports;

class CrashReport {
    friend TableCrashReports;

public:
    CrashReport(std::string id, std::string component);
    [[nodiscard]] std::string id() const;
    [[nodiscard]] std::string component() const;

private:
    const std::string _id;
    const std::string _component;
};

#endif
