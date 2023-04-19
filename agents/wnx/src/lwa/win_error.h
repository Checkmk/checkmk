// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef win_error_h
#define win_error_h

#include <stdexcept>
#include <string>

class WinApiInterface;

#define GET_LAST_ERROR \
    0xffffffff  // Hopefully this is not used by any real function!

std::string get_win_error_as_string(unsigned long error_id = GET_LAST_ERROR);

#endif  // win_error_h
