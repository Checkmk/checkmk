
// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_details_h__
#define fileinfo_details_h__

#include <filesystem>
#include <string>

#include "cma_core.h"
#include "section_header.h"

#include "providers/internal.h"

namespace cma::provider::details {

bool ValidFileInfoPathEntry(const std::string Entry);
std::string ProcessFileInfoPathEntry(const std::string Entry);
}  // namespace cma::provider::details

namespace cma::provider::details {

// ------------------------------------------------------
// Scanners:
// ------------------------------------------------------
void GatherMatchingFilesRecursive(
    const std::filesystem::path &SearchPath,   // dir from which we begin
                                               // funny recursive search
    const std::filesystem::path &FilePattern,  // full mask from yaml
                                               // fileinfo.path
    PathVector &Files) noexcept;               // input and output

void GatherMatchingFilesAndDirs(const std::filesystem::path &searchPath,
                                const std::filesystem::path &filePattern,
                                const std::filesystem::path &dirPattern,
                                PathVector &files, PathVector &dirs);

// MAIN API C ALL
PathVector FindFilesByMask(const std::wstring Mask);

// ------------------------------------------------------
// Globs:
// ------------------------------------------------------
enum class GlobType { kNone, kSimple, kRecursive };

// check for presense *, ? or *
GlobType DetermineGlobType(const std::wstring &Input);

// Build correct string for output
std::string MakeFileInfoString(const std::filesystem::path &FilePath);

// ------------------------------------------------------
// Specials:
// ------------------------------------------------------
std::filesystem::path GetOsPathWithCase(
    const std::filesystem::path &filePath) noexcept;

// ------------------------------------------------------
// Splitters:
// ------------------------------------------------------
// split the file path into two parts head and body
// c:\path\to -> [c:\] + [path\to]
// \\SRV_01\path\to -> [\\SRV_01\] + [path\to]
// supported only full path c:path\to do not supported, for example
// returns both empty if something is wrong
inline auto SplitFileInfoPathSmart(const std::filesystem::path &FilePath) {
    try {
        auto root_name = FilePath.root_name();
        auto root_dir = FilePath.root_directory();
        auto relative_path = FilePath.relative_path();
        if (root_name.u8string().empty() ||      // must be present
            root_dir.u8string().empty() ||       // must be present
            relative_path.u8string().empty()) {  // must be present
            XLOG::d("Path {} is not suitable", FilePath.u8string());
        } else
            return std::make_tuple(root_name / root_dir, relative_path);
    } catch (...) {
        XLOG::l("{} cannot be split correctly",
                FilePath.empty() ? "" : FilePath.u8string());
    }
    return std::make_tuple(std::filesystem::path(), std::filesystem::path());
}

}  // namespace cma::provider::details

#endif  // fileinfo_details_h__
