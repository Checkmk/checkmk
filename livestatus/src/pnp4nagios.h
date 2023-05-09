// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef pnp4nagios_h
#define pnp4nagios_h

#include "config.h"  // IWYU pragma: keep

#include <filesystem>
#include <string>

int pnpgraph_present(const std::filesystem::path &pnp_path,
                     const std::string &host, const std::string &service);

#endif  // pnp4nagios_h
