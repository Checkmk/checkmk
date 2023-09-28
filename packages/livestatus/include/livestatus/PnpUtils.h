// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef PnpUtils_h
#define PnpUtils_h

#include <string>

inline std::string dummy_service_description() { return "_HOST_"; }

std::string pnp_cleanup(const std::string &name);

#endif  // PnpUtils_h
