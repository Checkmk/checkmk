// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef OStreamStateSaver_h
#define OStreamStateSaver_h

#include "config.h"  // IWYU pragma: keep
#include <iostream>

class OStreamStateSaver {
public:
    explicit OStreamStateSaver(std::ostream &os)
        : _os(os)
        , _old_flags(_os.flags())
        , _old_precision(_os.precision())
        , _old_fill(_os.fill()) {}
    ~OStreamStateSaver() {
        _os.fill(_old_fill);
        _os.precision(_old_precision);
        _os.flags(_old_flags);
    }

private:
    std::ostream &_os;
    std::ios_base::fmtflags _old_flags;
    std::streamsize _old_precision;
    char _old_fill;
};

#endif  // OStreamStateSaver_h
