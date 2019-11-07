#ifndef CrashReport_h
#define CrashReport_h

#include <filesystem>
#include <functional>
#include <string>

class TableCrashReports;

class CrashReport {
    friend TableCrashReports;

public:
    CrashReport(std::string id, std::string component);
    [[nodiscard]] std::string id() const;
    [[nodiscard]] std::string component() const;

private:
    std::string _id;
    std::string _component;
};

/// Apply fun to every crash report under base_path.
void for_each_crash_report(const std::filesystem::path &base_path,
                           const std::function<void(const CrashReport &)> &);

#endif
