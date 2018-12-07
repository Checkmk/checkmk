// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "SectionFileinfo.h"
#include <chrono>
#include <cstring>
#include <iomanip>
#include <regex>
#include <sstream>
#include "Logger.h"
#include "SectionHeader.h"

namespace {

namespace chrono = std::chrono;
using namespace std::placeholders;

using GlobPairT = std::pair<std::wstring, bool>;
using PathDiffT = fs::path::const_iterator::difference_type;
using TraversalFuncT =
    std::function<void(const fs::path &, const fs::path &, PathsT &, PathsT &)>;

enum class GlobType { None, Simple, Recursive };

/** Build the drive letter and root directory part of the given path if present.
 *
 * @param[in] filePath    The input path
 * @return                The drive letter and root directory if present and
 *                        number of elements that were consumed from the path
 *                        since path.begin()
 */
std::pair<fs::path, PathDiffT> buildPathBeginning(const fs::path &filePath) {
    fs::path beginning;
    PathDiffT diff = 0;
    const std::wregex drive{L"^[A-Za-z]:$"};
    auto it = filePath.begin(), end = filePath.end();
    std::wsmatch match;

    // If path starts with drive letter, just add it to the beginning.
    if (const auto str = it->wstring();
        it != end && std::regex_match(str, match, drive)) {
        beginning += *it++;
        ++diff;
    }

    // Append possible root directory.
    if (const auto str = it->wstring();
        it != end && (str == L"/" || str == L"\\")) {
        beginning /= *it;
        ++diff;
    }

    return {beginning, diff};
}

// Traits class for switching between recursive and non-recursive versions of
// directory_iterator in std::[experimental::]filesystem.
template <bool recursive>
struct IteratorTraits {
    using iterator_type = fs::recursive_directory_iterator;
};

template <>
struct IteratorTraits<false> {
    using iterator_type = fs::directory_iterator;
};

/**
 * Iterate through given search path and append found files and directories to
 * given containers. The template parameter decides if recursive or
 * non-recursive directory traversal should be used.
 *
 * @param[in]      searchPath        The search path to iterate through
 * @param[in]      filePattern       The glob pattern found files must match
 * @param[in]      dirPattern        The glob pattern found dirs must match
 * @param[in/out]  files             The container for storing found files
 * @param[in/out]  dirs              The container for storing found dirs
 */
// The function works not so good as we are expecting:
// dir traverse doesn't work, symlinks are not processed too,
// unit tests are absent(refactoring is forbidden)
// i.e. pure disaster. Do not reuse without careful testing.
// Or just do not reuse.
template <bool recursive>
void addFilesAndDirs(const fs::path &searchPath, const fs::path &filePattern,
                     const fs::path &dirPattern, PathsT &files, PathsT &dirs) {
    using IteratorT = typename IteratorTraits<recursive>::iterator_type;
    for (const auto &p : IteratorT(searchPath)) {
        // Found files must match the entire path pattern.

        // *******************************************
        // we have to check status, not symlink_status
        // if you are not sure, test behavior before
        // putting the code into production
        auto status = p.status();  // CMK-1417, to be confirmed in ticket

        // Logic below is a bit crazy and ineffective(we check status twice)
        // correct is "double if", not logical AND.

        // normal file
        if (fs::is_regular_file(status) &&
            globmatch(filePattern.wstring(), p.path().wstring())) {
            files.push_back(p.path());
            // Only consider dirs if not iterating recursively.
            // Found dirs must match the pattern only on the next subdir
            // level.
            continue;
        }

        // directory
        if (!recursive && fs::is_directory(status) &&
            globmatch(dirPattern.wstring(), p.path().wstring())) {
            dirs.push_back(p.path());
            continue;
        }
    }
}

/**
 * Find files and directories on the next subdirectory level.
 *
 * @param[in]    subdir               The subdirectory
 * @param[in]    basedirs             The base dirs from which to look downwards
 * @param[in]    logger               The logger instance
 * @param[in]    traversalFunction    Traversal function to collect files and
 *                                    dirs recursively or non-recursively.
 * @return                            A pair of found files and dirs
 */
std::pair<PathsT, PathsT> findFilesAndDirsInSubdir(
    const fs::path &subdir, const PathsT &basedirs, Logger *logger,
    const TraversalFuncT &traversalFunction) {
    PathsT files, dirs;
    for (const auto &dir : basedirs) {
        auto dirPattern = dir / subdir;
        try {
            traversalFunction(dir, dirPattern, files, dirs);
        } catch (const fs::filesystem_error &e) {
            // May occur if iterating a non-existing path. May be a sign of
            // faulty config, but nothing catastrophic -> just debug log.
            Debug(logger) << e.what();
        }
    }

    return {files, dirs};
}

/**
 * Switch between recursive and non-recursive versions of directory traversal.
 * Additionally, bind the glob pattern for matching found files to a parameter
 * of the switched function implementation.
 *
 * @param[in]    recursive     True if subdirs are searched recursively
 * @param[in]    filePattern   The glob pattern found files must match
 * @return                     Function for collecting files and directories in
 *                             a directory recursively or non-recursively.
 */
inline TraversalFuncT switchDirTraversalFunction(bool recursive,
                                                 const fs::path &filePattern) {
    const auto &traversalFunction =
        recursive ? addFilesAndDirs<true> : addFilesAndDirs<false>;
    return std::bind(traversalFunction, _1, std::ref(filePattern), _2, _3, _4);
}

/**
 * Find out if input param contains any of the glob patterns **, * or ?.
 *
 * @param[in]    glob    The candidate glob
 * @return               An enumeration value: None if no glob pattern
 *                                             Simple if * or ?
 *                                             Recursive if **
 */
GlobType determineGlobType(const std::wstring &glob) {
    const std::array<GlobPairT, 3> globPatterns = {
        std::make_pair(L"^\\*\\*$", true),  //
        std::make_pair(L".*\\*.*", false),  //
        std::make_pair(L".*\\?.*", false)   //
    };

    auto it = std::find_if(globPatterns.cbegin(), globPatterns.cend(),
                           [&glob](const auto &pattern) {
                               std::wsmatch match;
                               return std::regex_match(
                                   glob, match, std::wregex(pattern.first));
                           });
    if (it == globPatterns.cend())
        return GlobType::None;
    else if (it->second)
        return GlobType::Recursive;
    else
        return GlobType::Simple;
}

inline PathsT sorted(PathsT &files) {
    std::sort(files.begin(), files.end());
    return files;
}

/**
 * Find files in given path that may contain glob patterns.
 *
 * @param[in]    path      The input path
 * @param[in]    logger    The logger instance
 * @return                 The found files
 */
PathsT findFiles(const fs::path &path, Logger *logger) {
    PathsT files;
    const auto &[searchPath, diff] = buildPathBeginning(path);
    PathsT dirs = {searchPath};

    // Iterate through the path element per element.
    for (auto it = std::next(path.begin(), diff), end = path.end(); it != end;
         ++it) {
        // If the element contains a glob pattern, find items in subdirs that
        // match the pattern. Pattern can be simple (* or ?) or recursive (**).
        if (auto globType = determineGlobType(it->wstring());
            globType != GlobType::None) {
            const auto traversalFunction = switchDirTraversalFunction(
                globType == GlobType::Recursive, path);
            const auto &[nextLevelFiles, nextLevelDirs] =
                findFilesAndDirsInSubdir(*it, dirs, logger, traversalFunction);
            files.reserve(files.size() + nextLevelFiles.size());
            std::copy(std::move_iterator(nextLevelFiles.begin()),
                      std::move_iterator(nextLevelFiles.end()),
                      std::back_inserter(files));
            // For recursive glob, the rest of the path was already traversed.
            if (globType == GlobType::Recursive) break;
            // If non-recursive, use next level subdirs for next iteration.
            dirs = std::move(nextLevelDirs);
        } else {
            // No glob pattern, next iteration will be done on next subdir level
            // by appending the path element to search path(s).
            std::transform(dirs.cbegin(), dirs.cend(), dirs.begin(),
                           [&it](const auto &dir) { return dir / *it; });
        }
    }
    // If the complete path represents an existing file, add it to found files.
    if (fs::is_regular_file(fs::symlink_status(path))) {
        files.push_back(path);
    }

    return sorted(files);
}

// fs::[recursive_]directory_iterator apparently contains a bug: it does not
// preserve the case for case-insensitive but case-preserving FSs like NTFS. To
// cope with this, fix the casing afterwards for found files. Of course, this
// would be too easy if it could be done for the complete path at once. MSDN
// provides us with an API that lets you do it just for the last, "basename"
// part of the path.
inline fs::path fixBasenameCase(const fs::path &filePath,
                                const WinApiInterface &winapi) {
    WIN32_FIND_DATAW fileData{0};
    SearchHandle handle{
        winapi.FindFirstFileW(filePath.wstring().c_str(), &fileData), winapi};
    return {fileData.cFileName};
}

// The case-preservation fun for the entire path.
fs::path correctPathCase(const fs::path &filePath,
                         const WinApiInterface &winapi) {
    auto [preserved, diff] = buildPathBeginning(filePath);

    // Append the rest of the part with fixed cases.
    for (auto it = std::next(filePath.begin(), diff), end = filePath.end();
         it != end; ++it) {
        preserved /= fixBasenameCase(preserved / *it, winapi);
    }

    return preserved;
}

// Terrible workaround for getting file size due to a bug in Mingw_w64
// cross-compiler implementation of std::experimental::filesystem::file_size
// with files exceeding 4 GB.
unsigned long long getFileSize(const fs::path &filePath, Logger *logger,
                               const WinApiInterface &winapi) {
    WIN32_FIND_DATA findData;
    SearchHandle findHandle{
        winapi.FindFirstFile(to_utf8(filePath.wstring()).c_str(), &findData),
        winapi};

    if (findHandle) {
        return static_cast<unsigned long long>(findData.nFileSizeLow) +
               (static_cast<unsigned long long>(findData.nFileSizeHigh) << 32);
    }

    Error(logger) << "Could not find file '" << Utf8(filePath) << "'";
    return 0;
}

void outputFileinfo(std::ostream &out, const fs::path &filePath, Logger *logger,
                    const WinApiInterface &winapi) {
    try {
        const auto finalPath = correctPathCase(filePath, winapi);
        out << Utf8(finalPath.wstring()) << "|"
            << getFileSize(finalPath, logger, winapi) << "|";
        const auto timeEntry = chrono::duration_cast<chrono::seconds>(
            fs::last_write_time(finalPath).time_since_epoch());
        out << timeEntry.count() << "\n";
    } catch (const fs::filesystem_error &e) {
        Error(logger) << e.what();
    }
}

void outputFileinfos(std::ostream &out, const fs::path &path, Logger *logger,
                     const WinApiInterface &winapi) {
    const auto filePaths = findFiles(path, logger);

    if (filePaths.empty()) {
        out << Utf8(path.wstring()) << "|missing|"
            << section_helpers::current_time() << "\n";
    }

    for (const auto &filePath : filePaths) {
        outputFileinfo(out, filePath, logger, winapi);
    }
}

}  // namespace

SectionFileinfo::SectionFileinfo(Configuration &config, Logger *logger,
                                 const WinApiInterface &winapi)
    : Section("fileinfo", config.getEnvironment(), logger, winapi,
              std::make_unique<SectionHeader<'|', SectionBrackets>>("fileinfo",
                                                                    logger))
    , _fileinfo_paths(config, "fileinfo", "path", winapi) {}

bool SectionFileinfo::produceOutputInner(std::ostream &out,
                                         const std::optional<std::string> &) {
    Debug(_logger) << "SectionFileinfo::produceOutputInner";
    out << section_helpers::current_time() << "\n";

    for (const auto &path : *_fileinfo_paths) {
        outputFileinfos(out, path, _logger, _winapi);
    }

    return true;
}
