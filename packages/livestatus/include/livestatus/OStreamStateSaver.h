// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OStreamStateSaver_h
#define OStreamStateSaver_h

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
