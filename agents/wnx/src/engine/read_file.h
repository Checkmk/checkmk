// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
std::ifstream OpenFileStream(const T *FileName) {
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
    if constexpr (sizeof(T) == 2) {
        XLOG::l("File '{}' not found in {}", wtools::ToUtf8(file_name),
                cur_dir);
    } else {
        XLOG::l("File '{}' not found in {}", file_name, cur_dir);
    }
}

inline uint32_t GetFileStreamSize(std::ifstream &f) {
    f.seekg(0, std::ios::end);
    const auto fsize = static_cast<uint32_t>(f.tellg());
    f.seekg(0, std::ios::beg);
    return fsize;
}

}  // namespace details

// more or less tested indirectly with test-player
template <typename T>
std::optional<std::vector<uint8_t>> ReadFileInVector(
    const T *file_name) noexcept {
    if (file_name == nullptr) {
        return {};
    }
    try {
        auto f = details::OpenFileStream(file_name);

        if (!f.good()) {
            details::DisplayReadFileError(file_name);
            return {};
        }

        const auto fsize = details::GetFileStreamSize(f);
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
}

inline std::optional<std::string> ReadFileInString(
    const std::string &file_name) noexcept {
    try {
        std::ifstream f(file_name.c_str(), std::ios::binary);
        if (!f.good()) {
            details::DisplayReadFileError(file_name.c_str());
            return {};
        }

        const auto fsize = details::GetFileStreamSize(f);
        std::string v;
        v.resize(fsize);
        f.read(v.data(), fsize);
        return v;
    } catch (const std::exception &e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
}

inline std::optional<std::string> ReadFileInString(
    const std::wstring &file_name) noexcept {
    try {
        std::ifstream f(file_name.c_str(), std::ios::binary);
        if (!f.good()) {
            details::DisplayReadFileError(file_name.c_str());
            return {};
        }

        const auto fsize = details::GetFileStreamSize(f);
        std::string v;
        v.resize(fsize);
        f.read(v.data(), fsize);
        return v;
    } catch (const std::exception &e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
}

inline std::optional<std::vector<uint8_t>> ReadFileInVector(
    const std::filesystem::path &file) noexcept {
    const auto path = file.wstring();
    if (path.empty()) {
        return {};
    }

    return ReadFileInVector(wtools::ToUtf8(path).c_str());
}

}  // namespace cma::tools
