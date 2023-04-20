// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Row_h
#define Row_h

class Row {
public:
    // Here we basically forget the actual type of the row...
    explicit Row(const void *ptr) : _ptr(ptr) {}

    // ... and here we reconstruct it, hopefully in a correct way. :-/
    template <typename T>
    [[nodiscard]] const T *rawData() const {
        return static_cast<const T *>(_ptr);
    }

    [[nodiscard]] bool isNull() const { return _ptr == nullptr; }

private:
    const void *_ptr;
};

#endif  // Row_h
