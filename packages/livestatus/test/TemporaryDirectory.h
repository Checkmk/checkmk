// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TemporaryDirectory_h
#define TemporaryDirectory_h

#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <system_error>

// A fresh directory below the system's temporary directory, removed together
// with its contents on destruction. Its unique name keeps concurrent test runs
// apart, and its path is short enough for Unix domain sockets within it.
class TemporaryDirectory {
public:
    explicit TemporaryDirectory(const std::string &prefix)
        : path_{create(prefix)} {}
    ~TemporaryDirectory() {
        std::error_code ec;  // ignored, we can't do anything about it
        std::filesystem::remove_all(path_, ec);
    }
    TemporaryDirectory(const TemporaryDirectory &) = delete;
    TemporaryDirectory &operator=(const TemporaryDirectory &) = delete;
    TemporaryDirectory(TemporaryDirectory &&) = delete;
    TemporaryDirectory &operator=(TemporaryDirectory &&) = delete;

    [[nodiscard]] const std::filesystem::path &path() const { return path_; }

private:
    std::filesystem::path path_;

    static std::filesystem::path create(const std::string &prefix) {
        auto path =
            (std::filesystem::temp_directory_path() / (prefix + "_XXXXXX"))
                .string();
        if (mkdtemp(path.data()) == nullptr) {
            throw std::system_error{errno, std::generic_category(),
                                    "cannot create temporary directory"};
        }
        return path;
    }
};

#endif  // TemporaryDirectory_h
