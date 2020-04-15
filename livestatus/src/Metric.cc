// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Metric.h"
#include <sstream>
#include "Logger.h"
#include "StringUtils.h"

void scan_rrd(const std::filesystem::path& basedir, const std::string& desc,
              Metric::Names& names, Logger* logger) {
    Informational(logger) << "scanning for metrics of " << desc << " in "
                          << basedir;
    std::string base = pnp_cleanup(desc + " ");
    try {
        for (const auto& entry : std::filesystem::directory_iterator(basedir)) {
            if (entry.path().extension() == ".rrd") {
                auto stem = entry.path().filename().stem().string();
                if (mk::starts_with(stem, base)) {
                    // NOTE: This is the main reason for mangling: The part of
                    // the file name after the stem is considered a mangled
                    // metric name.
                    names.emplace_back(stem.substr(base.size()));
                }
            }
        }
    } catch (const std::filesystem::filesystem_error& e) {
        if (e.code() == std::errc::no_such_file_or_directory) {
            Debug(logger) << "directory " << basedir << " does not exist yet";
        } else {
            Warning(logger) << "scanning directory for metrics: " << e.what();
        }
    }
}
