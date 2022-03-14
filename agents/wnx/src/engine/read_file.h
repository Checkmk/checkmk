// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <vector>

#include "common/wtools.h"
#include "logger.h"
#include "tools/_xlog.h"

namespace cma::tools {

namespace details {

template <typename T>
inline std::ifstream OpenFileStream(const T *FileName) {
#if defined(_MSC_BUILD)
    std::ifstream f(FileName, std::ios::binary);
#else
    // GCC can't wchar, conversion required
    std::basic_string<T> str(FileName);
    std::string file_name(str.begin(), str.end());
    std::ifstream f(file_name, std::ios::binary);
#endif
    return f;
}

template <typename T>
void DisplayReadFileError(const T *file_name) {
    std::error_code ec;
    auto cur_dir = std::filesystem::current_path(ec);
    if constexpr (sizeof(T) == 2)
        XLOG::l("File '{}' not found in {}", wtools::ToUtf8(file_name),
                cur_dir);
    else
        XLOG::l("File '{}' not found in {}", file_name, cur_dir);
}

inline uint32_t GetFileStreamSize(std::ifstream &f) {
    // size obtain
    f.seekg(0, std::ios::end);
    auto fsize = static_cast<uint32_t>(f.tellg());

    // read contents
    f.seekg(0, std::ios::beg);
    return fsize;
}

}  // namespace details

// more or less tested indirectly with test-player
template <typename T>
std::optional<std::vector<uint8_t>> ReadFileInVector(
    const T *FileName) noexcept {
    if (FileName == nullptr) return {};
    try {
        auto f = details::OpenFileStream(FileName);
        /*
        #if defined(_MSC_BUILD)
                std::ifstream f(FileName, std::ios::binary);
        #else
                // GCC can't wchar, conversion required
                std::basic_string<T> str(FileName);
                std::string file_name(str.begin(), str.end());
                std::ifstream f(file_name, std::ios::binary);
        #endif
        */

        if (!f.good()) {
            details::DisplayReadFileError(FileName);
            return {};
        }

        auto fsize = details::GetFileStreamSize(f);
        std::vector<uint8_t> v;
        v.resize(fsize);
        f.read(reinterpret_cast<char *>(v.data()), fsize);
        return v;
    } catch (const std::exception &e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
    return {};
}

template <typename T>
std::optional<std::string> ReadFileInString(const T *FileName) noexcept {
    try {
#if defined(_MSC_BUILD)
        std::ifstream f(FileName, std::ios::binary);
#else
        // GCC can't wchar, conversion required
        std::basic_string<T> str(FileName);
        std::string file_name(str.begin(), str.end());
        std::ifstream f(file_name, std::ios::binary);
#endif

        if (!f.good()) {
            details::DisplayReadFileError(FileName);
            return {};
        }

        auto fsize = details::GetFileStreamSize(f);
        std::string v;
        v.resize(fsize);
        f.read(reinterpret_cast<char *>(v.data()), fsize);
        return v;
    } catch (const std::exception &e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
    return {};
}

inline std::optional<std::vector<uint8_t>> ReadFileInVector(
    const std::filesystem::path &File) noexcept {
    auto path = File.u8string();
    if (path.empty()) return {};

    return ReadFileInVector(path.c_str());
}

}  // namespace cma::tools
