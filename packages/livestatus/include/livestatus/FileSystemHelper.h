// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef FileSystemHelper_h
#define FileSystemHelper_h

#include <filesystem>
#include <string>

namespace mk {

/// Replace \\\\ with \\, and \\s with space.
std::string unescape_filename(const std::string &filename);

/// Return true if path is in directory, otherwise return false.
/// The function always returns false if path does not exist.
bool path_contains(const std::filesystem::path &directory,
                   const std::filesystem::path &path);

}  // namespace mk

#endif
