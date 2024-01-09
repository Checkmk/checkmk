// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/CrashReport.h"

#include <optional>
#include <regex>
#include <system_error>

#include "livestatus/Logger.h"

// TODO(ml): This would be cleaner with ranges.
bool mk::crash_report::any(
    const std::filesystem::path &base_path,
    const std::function<bool(const CrashReport &)> &fun) {
    const std::regex uuid_pattern(
        R"(^\S{4}(?:\S{4}-){4}\S{12}$)",
        std::regex_constants::ECMAScript | std::regex_constants::icase);
    if (!std::filesystem::is_directory(base_path)) {
        return false;
    }
    for (const auto &component_dir :
         std::filesystem::directory_iterator(base_path)) {
        if (!component_dir.is_directory()) {
            continue;
        }
        for (const auto &id_dir :
             std::filesystem::directory_iterator(component_dir)) {
            if (!(id_dir.is_directory() and
                  std::regex_search(id_dir.path().stem().string(),
                                    uuid_pattern))) {
                continue;
            }
            if (fun(CrashReport{
                    .id = id_dir.path().stem(),
                    .component = component_dir.path().stem(),
                })) {
                return true;
            }
        }
    }
    return false;
}

bool mk::crash_report::delete_id(const std::filesystem::path &base_path,
                                 const std::string &id, Logger *logger) {
    std::optional<CrashReport> target;
    mk::crash_report::any(base_path, [&target, &id](const CrashReport &cr) {
        if (cr.id == id) {
            target = cr;
            return true;
        }
        return false;
    });
    if (!target) {
        return false;
    }
    std::error_code ec;
    std::filesystem::remove_all(base_path / target->component / target->id, ec);
    if (ec) {
        Debug(logger) << "Failed to remove the crash report " << target->id;
        return false;
    }
    Debug(logger) << "Successfully removed the crash report " << target->id;
    return true;
}
