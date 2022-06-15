// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// data owners  here

#pragma once
namespace cma::tools {
// ownership belongs to DataBlock
// supplementary structure to store data
// tested in perf_reader.exe(part of the old win agent)
// NOT THREAD SAFE
template <typename T>
struct DataBlock {
    DataBlock() : len_(0), data_(nullptr) {}
    DataBlock(int Size, T* Buffer) : len_(Size), data_(Buffer) {}
    ~DataBlock() { delete[] data_; }

    // no copy:
    DataBlock(const DataBlock&) = delete;
    DataBlock& operator=(const DataBlock&) = delete;

    // default move
    DataBlock(DataBlock&& Rhs)  noexcept {
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
    }

    DataBlock& operator=(DataBlock&& Rhs)  noexcept {
        delete[] data_;
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
        return *this;
    }

    int len_;
    T* data_;
};

}  // namespace cma
