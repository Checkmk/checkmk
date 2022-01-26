// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#if defined(_WIN32)
#include <conio.h>
#else
#include "curses.h"
#endif

namespace cma::tools {
inline int GetKeyPress() {
#if defined(_WIN32)
    return _getch();
#else
    return getch();
#endif
}
}  // namespace cma::tools
