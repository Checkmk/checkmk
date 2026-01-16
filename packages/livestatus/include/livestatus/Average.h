// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Average_h
#define Average_h

#include <chrono>
#include <mutex>

class Average {
public:
    void update(double value);
    [[nodiscard]] double get() const {
        const std::scoped_lock sl{_lock};
        return _average;
    }

private:
    std::chrono::steady_clock::time_point _last_update;
    double _average{0};
    mutable std::mutex _lock;
};

#endif  // Average_h
