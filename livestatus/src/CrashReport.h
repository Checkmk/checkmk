// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CrashReport_h
#define CrashReport_h

#include "config.h"  // IWYU pragma: keep

#include <filesystem>
#include <functional>
#include <string>

class Logger;
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

namespace mk::crash_report {

/// Apply fun to crash reports under base_path until fun returns `true`
/// or every crash report has been visited.
bool any(const std::filesystem::path &base_path,
         const std::function<bool(const CrashReport &)> &fun);

/// \brief Delete a crash report with `id`.
///
/// Returns `true` if the crash report was successfully deleted, otherwise
/// returns `false`.
bool delete_id(const std::filesystem::path &base_path, const std::string &id,
               Logger *logger);

}  // namespace mk::crash_report

#endif
