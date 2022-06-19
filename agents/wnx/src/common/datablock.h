// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// data owners  here

#pragma once
namespace cma::tools {
// ownership belongs to DataBlock
// supplementary structure to store data
// tested in perf_reader.exe(part of the old win agent)
// NOT THREAD SAFE
template <typename T>
struct DataBlock {
    DataBlock() = default;
    DataBlock(int size, T *buffer) : len_(size), data_(buffer) {}
    ~DataBlock() { delete[] data_; }

    // no copy:
    DataBlock(const DataBlock &) = delete;
    DataBlock &operator=(const DataBlock &) = delete;

    // default move
    DataBlock(DataBlock &&rhs) noexcept {
        data_ = rhs.data_;
        len_ = rhs.len_;
        rhs.data_ = nullptr;
        rhs.len_ = 0;
    }

    DataBlock &operator=(DataBlock &&rhs) noexcept {
        delete[] data_;
        data_ = rhs.data_;
        len_ = rhs.len_;
        rhs.data_ = nullptr;
        rhs.len_ = 0;
        return *this;
    }

    int len_{0};
    T *data_{nullptr};
};

}  // namespace cma::tools
