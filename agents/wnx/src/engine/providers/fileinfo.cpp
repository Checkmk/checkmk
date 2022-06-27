
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/fileinfo.h"

#include <fmt/format.h>

#include <filesystem>
#include <regex>
#include <string>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "glob_match.h"
#include "logger.h"
#include "providers/fileinfo_details.h"
#include "tools/_raii.h"

namespace fs = std::filesystem;

namespace cma::provider::details {

std::optional<std::chrono::system_clock::duration> GetFileTimeSinceEpoch(
    const fs::path &file) noexcept {
    std::error_code ec;
    auto file_last_touch_full = fs::last_write_time(file, ec);
    if (ec.value()) {
        return {};
    }
    return file_last_touch_full.time_since_epoch();
}

/// Get the OS filename preserving the filename case. This is Windows FS.
// on error returns same name
fs::path ReadBaseNameWithCase(const fs::path &file_path) {
    WIN32_FIND_DATAW file_data{0};
    auto *handle = ::FindFirstFileW(file_path.wstring().c_str(), &file_data);
    if (wtools::IsInvalidHandle(handle)) {
        XLOG::t.w("Unexpected status [{}] when reading file '{}'",
                  ::GetLastError(), file_path);
        return file_path;
    }
    ON_OUT_OF_SCOPE(::FindClose(handle));
    return {file_data.cFileName};
}

namespace {
void UppercasePath(fs::path &path) {
    auto str = path.wstring();
    tools::WideUpper(str);
    path = str;
}
}  // namespace

/// read file name preserving case, the head is uppercased( C:, for example)
fs::path GetOsPathWithCase(const fs::path &file_path) {
    auto [head_part, body] = details::SplitFileInfoPathSmart(file_path);

    UppercasePath(head_part);
    if (head_part.empty() && body.empty())
        body = file_path;  // unusual case, only name

    // Scan all path and read for every chunk correct representation
    // from OS
    for (const auto &part : body) {
        head_part /= ReadBaseNameWithCase(head_part / part);
    }
    return head_part;
}

// Find out if input param contains any of the glob patterns **, * or ?.
//
// return               An enumeration value: None if no glob pattern
//                                            Simple if * or ?
//                                            Recursive if **
GlobType DetermineGlobType(const std::wstring &input) {
    const std::pair<std::wstring, GlobType> matches[] = {
        {L"^\\*\\*$", GlobType::kRecursive},  // "**"
        {L".*\\*.*", GlobType::kSimple},      // "anything*anything"
        {L".*\\?.*", GlobType::kSimple}       // "anything?anything"
    };

    std::wsmatch match;
    try {
        for (const auto &[regex_str, glob_type] : matches) {
            if (std::regex_match(input, match, std::wregex(regex_str))) {
                return glob_type;
            }
        }
    } catch (const std::exception &e) {
        XLOG::l("Bad pattern {} '{}'", wtools::ToUtf8(input), e.what());
    }

    return GlobType::kNone;
}

/// Gathers ALL FILES that match file pattern
//
// and adds(!) them to input parameter
// Search path is starting point for recursive search
// File pattern is original value from yaml.fileinfo.path[n]
void GatherMatchingFilesRecursive(const fs::path &search_path,
                                  const fs::path &file_pattern,
                                  PathVector &files) {
    try {
        for (const auto &entry : fs::recursive_directory_iterator(
                 search_path, fs::directory_options::skip_permission_denied)) {
            std::error_code ec;
            auto status = entry.status(ec);
            const auto &entry_name = entry.path();
            if (ec) {
                XLOG::t("Access to '{}' is not possible, status [{}]",
                        entry_name.u8string(), ec.value());
                continue;
            }

            if (!fs::is_regular_file(status)) {
                continue;
            }

            if (tools::GlobMatch(file_pattern.wstring(),
                                 entry_name.wstring())) {
                files.push_back(entry);
            }
        }
    } catch (std::exception &e) {
        XLOG::l("Exception recursive '{}'", e.what());
    } catch (...) {
        XLOG::l("Exception recursive");
    }
}

/// Scans one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const fs::path &search_dir,    // c:\windows
    const fs::path &dir_pattern,   // c:\windows\L*
    const fs::path &file_pattern,  // c:\windows\L*\*.log
    PathVector &files_found,       // output
    PathVector &dirs_found) {      // output
    for (const auto &p : fs::directory_iterator(search_dir)) {
        std::error_code ec;
        auto status = p.status(ec);  // CMK-1417
        if (ec) {
            XLOG::d("Cant obtain status for dir '{}' path '{}' error [{}]",
                    search_dir, p.path(), ec.value());
            continue;
        }

        const auto &path = p.path();
        try {
            if (fs::is_regular_file(status) &&
                tools::GlobMatch(file_pattern.wstring(), path.wstring())) {
                files_found.push_back(path);
                continue;
            }

            if (fs::is_directory(status) &&
                tools::GlobMatch(dir_pattern.wstring(), path.wstring())) {
                dirs_found.push_back(path);
                continue;
            }
        } catch (std::exception &e) {
            XLOG::l("Exception GatherMatchingFilesAndDirs '{}'", e.what());
        }
    }
}

}  // namespace cma::provider::details

namespace cma::provider::details {

//
// Find files and directories on the next subdirectory level.
//
// @param[in]    DirsToSearch       The base dirs from which to look
// @param[in]    PatternToUse       The subdirectory to start search
// @param[in]    Mask               From the ini/yaml file
// @return                          A pair of found files and dirs
std::pair<PathVector, PathVector> FindFilesAndDirsInSubdir(
    const PathVector &dirs_to_search, const fs::path &pattern_to_use,
    const fs::path &mask) {
    PathVector files;
    PathVector dirs;
    for (const auto &dir : dirs_to_search) {
        auto pattern_to_check = dir / pattern_to_use;
        GatherMatchingFilesAndDirs(dir, pattern_to_check, mask, files, dirs);
    }

    return {files, dirs};
}

PathVector FindFilesAndDirsInSubdirRecursive(const PathVector &dirs_to_search,
                                             const fs::path &mask) {
    PathVector files;
    for (const auto &dir : dirs_to_search) {
        GatherMatchingFilesRecursive(dir, mask, files);
    }

    return files;
}

namespace {
/// Builds files vector from the dirs and tail, updates dirs from dirs and tail
//
// Rebuild dirs by adding tail to create path array from possible entries
// - kill dirs
// - process all entries:
//   - if resulting entry is existing dir, then add to dirs
//   - if resulting entry is file, then add to files
void ProcessDirsAndFilesTables(PathVector &dirs, PathVector &files,
                               const fs::path &tail) {
    for (auto &entry : dirs) {
        entry /= tail;
    }

    // check what the hell we have in dirs and update files
    for (auto &entry : dirs) {
        std::error_code ec;
        auto good_file = fs::is_regular_file(entry, ec);
        if (ec) {  // not found, reporting only when error is serious
            if (ec.value() != 2) {  // 2 means NOT FOUND, this is ok
                // low probability. Something really bad
                XLOG::t("Cant access file '{}' status [{}]", entry, ec.value());
            }
            continue;
        }

        if (good_file) {
            // good boy found, push it the files
            files.push_back(entry);
        }
    }

    // remove non-dirs entry from dirs table
    auto last_pos =
        std::remove_if(dirs.begin(), dirs.end(), [](const auto &path) {
            std::error_code ec;
            auto is_dir = fs::is_directory(path, ec);
            if (!ec) {
                return !is_dir;  // remove all what is not dir
            }

            if (ec.value() != 2) {
                // we write warning only for bad access writes and so on
                // not found in this case acceptable
                XLOG::d("Suspicious dir '{}' status [{}]", path, ec.value());
            }
            return true;  // remove trash with error too
        });

    dirs.erase(last_pos, dirs.end());
}

void AddVectorWithMove(PathVector &files, PathVector &found_files) {
    files.reserve(files.size() + found_files.size());
    std::copy(std::move_iterator(found_files.begin()),
              std::move_iterator(found_files.end()), std::back_inserter(files));
}
}  // namespace

PathVector FindFileBySplittedPath(const fs::path &head,         // "c:\"
                                  const fs::path &body,         // path
                                  const std ::wstring &mask) {  // c:\x\*x.txt
    PathVector dirs = {head};
    PathVector files;

    // Code below is verified and modified code from legacy agent
    // Iterate through the path element per element
    // c:\a\b\c\d => for c:\, a, b, c, d ....
    // we checking for a, b, c, d contains glob.
    // If contains, then we scan for all inside
    // If not, we just update our lists, dirs & files
    auto end = body.end();
    for (auto it = body.begin(); it != end; ++it) {
        auto glob_type = details::DetermineGlobType(it->wstring());
        // no pattern, just add to all dirs we have
        if (glob_type == GlobType::kNone) {
            ProcessDirsAndFilesTables(dirs, files, *it);
            continue;
        }
        // trivial case
        if (glob_type == GlobType::kSimple) {
            auto [found_files, found_dirs] =
                FindFilesAndDirsInSubdir(dirs, *it, mask);
            // add files to table
            AddVectorWithMove(files, found_files);

            // replace(!) dir table
            dirs = std::move(found_dirs);
            continue;
        }
        // For recursive glob, the rest of the path was already traversed.
        auto found_files = FindFilesAndDirsInSubdirRecursive(dirs, mask);
        AddVectorWithMove(files, found_files);
        break;
    }

    std::ranges::sort(files);

    return files;
}

// **********************************************************
// make a vector from all possible file existing on mask path
// empty vector on failure
//
// it/*/file should returns
// it/a/file
// it/b/file
// it/c/file

PathVector FindFilesByMask(const std::wstring &mask) {
    std::error_code ec;
    if (fs::is_regular_file(mask, ec)) {
        XLOG::t("Found regular file as path '{}'", wtools::ToUtf8(mask));
        return {fs::path(mask)};
    }
    auto [head_out, body_out] = details::SplitFileInfoPathSmart(mask);
    if (head_out.empty() || body_out.empty()) {
        return {};
    }
    return FindFileBySplittedPath(head_out, body_out, mask);
}

bool ValidFileInfoPathEntry(std::string_view entry) {
    fs::path p{wtools::ConvertToUTF16(entry)};
    return !p.root_name().empty() && !p.root_directory().empty();
}

std::string MakeFileInfoEntryModern(const fs::path &file_name, bool stat_failed,
                                    uint64_t file_size, int64_t seconds) {
    if (stat_failed) {
        return file_name.u8string() + FileInfo::kSep +
               std::string(FileInfo::kStatFailed) + "\n";
    }

    return fmt::format("{0}{1}{2}{1}{3}{1}{4}\n", file_name, FileInfo::kSep,
                       FileInfo::kOk, file_size, seconds);
}

std::string MakeFileInfoEntryLegacy(const fs::path &file_name, bool stat_failed,
                                    uint64_t file_size, int64_t seconds) {
    if (stat_failed) {
        return fmt::format("{0}{1}{2}{1}{3}\n", file_name, FileInfo::kSep,
                           FileInfo::kMissing, seconds);
    }

    return fmt::format("{0}{1}{2}{1}{3}\n", file_name, FileInfo::kSep,
                       file_size, seconds);
}

namespace {
void CorrectSeconds(int64_t &seconds) {
    // NOTE: This is a windows hack. Temporary till C++ 20 will be fully
    // implemented.
    // WHY: Windows filetime type std::filesystem has an epoch dated
    // to 1.01.1601. We need Unix epoch dated to 01.01.1970. Distance is
    // introduced as a constexpr value.
    // For the case if Microsoft will change *again* opinion about
    // epoch(experimental::filesystem are using Unix epoch), we check the
    // returned value.
    // To remove hack we need *to_time_t* functionality

    constexpr int64_t epoch_distance = 11'644'473'600LL;
    if (seconds > epoch_distance) {
        seconds -= epoch_distance;
    }
}

std::tuple<uint64_t, int64_t, bool> GetFileStats(const fs::path &file_path) {
    std::error_code ec;
    auto file_size = fs::file_size(file_path, ec);
    bool stat_failed = false;
    if (ec) {
        XLOG::l.e("Can't get size of file '{}'  status [{}]", file_path,
                  ec.value());
        file_size = 0;
        stat_failed = true;
    }

    int64_t seconds = 0;

    auto file_last_touch = GetFileTimeSinceEpoch(file_path);
    if (file_last_touch.has_value()) {
        auto duration =
            std::chrono::duration_cast<std::chrono::seconds>(*file_last_touch);
        seconds = duration.count();
        CorrectSeconds(seconds);
    } else {
        XLOG::l.e("Can't get last touch of file '{}' status [{}]", file_path,
                  ec.value());
        seconds = tools::SecondsSinceEpoch();
        stat_failed = true;
    }

    return {file_size, seconds, stat_failed};
}

std::tuple<uint64_t, int64_t, bool> GetFileStatsCreative(
    const fs::path &file_path) {
    std::error_code ec;
    uint64_t file_size{0U};
    int64_t seconds{0};
    bool stat_failed = true;
    for (auto const &dir_entry :
         fs::directory_iterator{file_path.parent_path()}) {
        if (tools::IsEqual(dir_entry.path().wstring(), file_path.wstring())) {
            file_size = dir_entry.file_size(ec);
            auto stamp = dir_entry.last_write_time().time_since_epoch();
            auto duration =
                std::chrono::duration_cast<std::chrono::seconds>(stamp);
            seconds = duration.count();
            CorrectSeconds(seconds);
            stat_failed = false;
            break;
        }
    }

    return {file_size, seconds, stat_failed};
}

}  // namespace

std::string MakeFileInfoStringMissing(const fs::path &file_name,
                                      FileInfo::Mode mode) {
    std::string out =
        file_name.u8string() + FileInfo::kSep + std::string(FileInfo::kMissing);

    // #deprecated
    if (mode == FileInfo::Mode::legacy) {
        out += FileInfo::kSep + std::to_string(tools::SecondsSinceEpoch());
    }

    out += "\n";

    return out;
}

std::string MakeFileInfoString(const fs::path &file_path, FileInfo::Mode mode) {
    std::error_code ec;
    auto presented = fs::exists(file_path, ec);
    auto file_name = GetOsPathWithCase(file_path);  // correct cases
    if (!presented && ec.value() != 32) {
        return MakeFileInfoStringMissing(file_name, mode);
    }
    auto [file_size, seconds, stat_failed] =
        presented ? GetFileStats(file_name) : GetFileStatsCreative(file_name);

    switch (mode) {
        case FileInfo::Mode::legacy:
            return MakeFileInfoEntryLegacy(file_name, stat_failed, file_size,
                                           seconds);
        case FileInfo::Mode::modern:
            return MakeFileInfoEntryModern(file_name, stat_failed, file_size,
                                           seconds);
    }
    // unreachable
    return {};
}

namespace {
bool IsDriveLetterAtTheStart(std::string_view text) noexcept {
    return text.size() > 2 && text[1] == ':' && std::isalpha(text[0]) != 0;
}

void CorrectDriveLetterByEntry(std::string &ret, std::string_view entry) {
    // drive letter correction:
    if (IsDriveLetterAtTheStart(entry) && IsDriveLetterAtTheStart(ret))
        ret[0] = entry[0];
}
}  // namespace
// single entry from config: a, b and c
// path: [a,b,c]
std::string ProcessFileInfoPathEntry(std::string_view entry,
                                     FileInfo::Mode mode) {
    // normal entry must be registered
    if (!FileInfo::ContainsGlobSymbols(entry)) {
        auto ret = MakeFileInfoString(entry, mode);
        CorrectDriveLetterByEntry(ret, entry);
        return ret;
    }

    // entries with glob patterns
    auto mask = wtools::ConvertToUTF16(entry);
    const auto file_paths = FindFilesByMask(mask);

    if (file_paths.empty()) {
        // no files? place missing entry(as 1.5 Agent)!
        return MakeFileInfoStringMissing(entry, mode);
    }

    std::string out;
    for (const auto &f : file_paths) {
        auto ret = MakeFileInfoString(f, mode);
        CorrectDriveLetterByEntry(ret, entry);
        out += ret;
    }

    return out;
}

}  // namespace cma::provider::details

namespace cma::provider {

void FileInfo::loadConfig() {}

// return array of path's if can otherwise nothing
std::optional<YAML::Node> GetPathArray(const YAML::Node &config) {
    try {
        const auto finfo_section = config[cfg::groups::kFileInfo];

        // sanity checks:
        if (!finfo_section) {
            XLOG::t("'{}' section absent", cfg::groups::kFileInfo);
            return {};
        }

        if (!finfo_section.IsMap()) {
            XLOG::d("'{}' is not correct", cfg::groups::kFileInfo);
            return {};
        }

        // get array, on success, return it
        const auto path_array = finfo_section[cfg::vars::kFileInfoPath];
        if (!path_array) {
            XLOG::t("'{}' section has no '{}' member", cfg::groups::kFileInfo,
                    cfg::vars::kFileInfoPath);
            return {};
        }

        if (!path_array.IsSequence()) {
            XLOG::l("'{}.{}' is malformed", cfg::groups::kFileInfo,
                    cfg::vars::kFileInfoPath);
            return {};
        }

        return path_array;
    } catch (const std::exception &e) {
        XLOG::l("CONFIG for '{}.{}' isn't valid, skipping. Exception '{}'",
                cfg::groups::kFileInfo, cfg::vars::kFileInfoPath, e.what());
        return {};
    }
}

namespace {
// we are using static outside functions to avoid(extremely rare)
// race condition. Theoretically any function can be called twice
// and init of functions statics may be a bit dangerous
const std::string g_modern_sub_header{
    "[[[header]]]\n"
    "name|status|size|time\n"
    "[[[content]]]\n"};
}  // namespace

std::string FileInfo::generateFileList(const YAML::Node &path_array) {
    int i_pos = 0;  // logging variable
    std::string out;
    for (const auto &p : path_array) {
        try {
            auto mask = p.as<std::string>();

            if (!details::ValidFileInfoPathEntry(mask)) {
                XLOG::d.t("'{}.{}[{}] = {}' is not valid, skipping",
                          cfg::groups::kFileInfo, cfg::vars::kFileInfoPath,
                          i_pos, mask);
                continue;
            }

            // mask is valid:
            auto ret = details::ProcessFileInfoPathEntry(mask, mode_);
            if (ret.empty()) continue;

            out += ret;
        } catch (const std::exception &e) {
            XLOG::l(
                "'{}.{}[{}]' is seriously not valid, skipping. Exception '{}'",
                cfg::groups::kFileInfo, cfg::vars::kFileInfoPath, i_pos,
                e.what());
        }
        i_pos++;
    }

    if (mode_ == Mode::modern) {
        return g_modern_sub_header + out;
    }

    return out;
}  // namespace provider

std::string FileInfo::makeBody() {
    auto out = std::to_string(tools::SecondsSinceEpoch()) + "\n";
    auto path_array_val = GetPathArray(cfg::GetLoadedConfig());
    return path_array_val.has_value() ? out + generateFileList(*path_array_val)
                                      : out;
}

bool FileInfo::ContainsGlobSymbols(std::string_view name) {
    return std::ranges::any_of(name,
                               [](char c) { return c == '*' || c == '?'; });
}
}  // namespace cma::provider
