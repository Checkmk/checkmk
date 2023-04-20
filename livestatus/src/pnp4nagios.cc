// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pnp4nagios.h"

#include <filesystem>
#include <system_error>

#include "livestatus/PnpUtils.h"

int pnpgraph_present(const std::filesystem::path &pnp_path,
                     const std::string &host, const std::string &service) {
    if (pnp_path.empty()) {
        return -1;
    }
    const std::filesystem::path path =
        pnp_path / pnp_cleanup(host) / (pnp_cleanup(service) + ".xml");
    std::error_code ec;
    (void)std::filesystem::status(path, ec);
    return ec ? 0 : 1;
}
