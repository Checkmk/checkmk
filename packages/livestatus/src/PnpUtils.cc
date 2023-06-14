// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/PnpUtils.h"

#include "livestatus/StringUtils.h"

std::string pnp_cleanup(const std::string &name) {
    return mk::replace_chars(name, R"( /\:)", '_');
}
