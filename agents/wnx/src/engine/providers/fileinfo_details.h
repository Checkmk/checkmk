// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_details_h__
#define fileinfo_details_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider::details {

bool ValidFileInfoPathEntry(std::string_view entry);
std::string ProcessFileInfoPathEntry(std::string_view entry,
                                     FileInfo::Mode mode);
}  // namespace cma::provider::details

namespace cma::provider::details {

// ------------------------------------------------------
// Scanners:
// ------------------------------------------------------
void GatherMatchingFilesRecursive(
    const std::filesystem::path &search_path,   // dir from which we begin
                                                // funny recursive search
    const std::filesystem::path &file_pattern,  // full mask from yaml
                                                // fileinfo.path
    PathVector &Files);                         // input and output

void GatherMatchingFilesAndDirs(
    const std::filesystem::path &search_dir,    // c:\windows
    const std::filesystem::path &dir_pattern,   // c:\windows\L*
    const std::filesystem::path &file_pattern,  // c:\windows\L*\*.log
    PathVector &files_found,                    // output
    PathVector &dirs_found);

// MAIN API C ALL
PathVector FindFilesByMask(const std::wstring &mask);

// ------------------------------------------------------
// Globs:
// ------------------------------------------------------
enum class GlobType { kNone, kSimple, kRecursive };

// check for presense *, ? or *
GlobType DetermineGlobType(const std::wstring &input);

// Build correct string for output
std::string MakeFileInfoString(const std::filesystem::path &file_path,
                               FileInfo::Mode mode);
std::string MakeFileInfoStringMissing(const std::filesystem::path &file_name,
                                      FileInfo::Mode mode);

// ------------------------------------------------------
// Specials:
// ------------------------------------------------------
std::filesystem::path GetOsPathWithCase(const std::filesystem::path &file_path);

/// Split the file path into two parts head and body.
//
// c:\path\to       -> [c:\]       + [path\to]
// \\SRV_01\path\to -> [\\SRV_01\] + [path\to]
// supported only full path 'c:path\to' do not supported, for example
// returns both empty if something is wrong
inline auto SplitFileInfoPathSmart(const std::filesystem::path &file_path) {
    try {
        auto root_name = file_path.root_name();
        auto root_dir = file_path.root_directory();
        auto relative_path = file_path.relative_path();

        if (root_name.u8string().empty() ||  //
            root_dir.u8string().empty() ||   //
            relative_path.u8string().empty()) {
            XLOG::d("Path '{}' is not suitable", file_path);
        } else
            return std::make_tuple(root_name / root_dir, relative_path);
    } catch (...) {
        XLOG::l("'{}' cannot be split correctly",
                file_path.empty() ? "" : file_path.u8string());
    }
    return std::make_tuple(std::filesystem::path(), std::filesystem::path());
}

}  // namespace cma::provider::details

#endif  // fileinfo_details_h__
