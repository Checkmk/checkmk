// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef mk_inventory_h
#define mk_inventory_h

#include "config.h"  // IWYU pragma: keep

#include <ctime>
#include <string>

time_t mk_inventory_last(const std::string &path);

#endif  // mk_inventory_h
