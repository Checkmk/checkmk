// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/mk_logwatch.h"

#include <system_error>

#include "livestatus/Logger.h"
#include "livestatus/PnpUtils.h"

void mk_logwatch_acknowledge(Logger *logger,
                             const std::filesystem::path &logwatch_path,
                             const std::string &host_name,
                             const std::string &file_name) {
    if (file_name.find('/') != std::string::npos) {
        Warning(logger) << "Invalid character / in mk_logfile filename '"
                        << file_name << "' of host '" << host_name << "'";
        return;
    }
    if (logwatch_path.empty()) {
        return;
    }
    auto path = std::filesystem::path(logwatch_path) / pnp_cleanup(host_name) /
                file_name;
    std::error_code ec;
    if (!std::filesystem::remove(path, ec)) {
        const generic_error ge("Cannot acknowledge mk_logfile file '" +
                               file_name + "' of host '" + host_name + "'");
        Warning(logger) << ge;
    }
}
