// .------------------------------------------------------------------------.
// |                ____ _               _        __  __ _  __              |
// |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
// |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
// |              | |___| | | |  __/ (__|   <    | |  | | . \               |
// |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
// |                                        |_____|                         |
// |             _____       _                       _                      |
// |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
// |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
// |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
// |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
// |                                     |_|                                |
// |                     _____    _ _ _   _                                 |
// |                    | ____|__| (_) |_(_) ___  _ __                      |
// |                    |  _| / _` | | __| |/ _ \| '_ \                     |
// |                    | |__| (_| | | |_| | (_) | | | |                    |
// |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
// |                                                                        |
// | mathias-kettner.com                                 mathias-kettner.de |
// '------------------------------------------------------------------------'
//  This file is part of the Check_MK Enterprise Edition (CEE).
//  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
//  Distributed under the Check_MK Enterprise License.
//
//  You should have  received  a copy of the Check_MK Enterprise License
//  along with Check_MK. If not, email to mk@mathias-kettner.de
//  or write to the postal address provided at www.mathias-kettner.de

#ifndef Average_h
#define Average_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>

// NOTE: The suppression below is necessary because cppcheck doesn't seem to
// understand default member initialization yet. :-/

// cppcheck-suppress noConstructor
class Average {
public:
    void update(double value);

private:
    std::chrono::steady_clock::time_point _last_update{};
    double _average{0};

    friend class TableStatus;  // for _average
};

#endif  // Average_h
