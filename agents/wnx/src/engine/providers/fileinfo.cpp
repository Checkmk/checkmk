
// provides basic api to start and stop service
#include "stdafx.h"

#include <filesystem>
#include <regex>
#include <string>
#include <tuple>

#include "fmt/format.h"

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "cfg.h"
#include "cma_core.h"
#include "glob_match.h"

#include "logger.h"

#include "providers/fileinfo.h"
#include "providers/fileinfo_details.h"

namespace cma::provider::details {

// read chunk from the file name preserving case
// on error - nothing
std::filesystem::path ReadBaseNameWithCase(
    const std::filesystem::path &FilePath) {
    WIN32_FIND_DATAW file_data{0};
    auto handle = ::FindFirstFileW(FilePath.wstring().c_str(), &file_data);
    if (handle == INVALID_HANDLE_VALUE) {
        XLOG::l.e("Unexpected status {} when reading file {} ", GetLastError(),
                  FilePath.u8string());
        return FilePath.wstring();
    }
    ON_OUT_OF_SCOPE(FindClose(handle));
    return {file_data.cFileName};
}

// read file name preserving case
// on error - nothing
std::filesystem::path GetOsPathWithCase(
    const std::filesystem::path &FilePath) noexcept {
    auto [head_part, body] = details::SplitFileInfoPathSmart(FilePath);
    {
        auto head = head_part.wstring();
        cma::tools::WideUpper(head);
        head_part = head;
    }

    // Scan all path and read for every chunk correct representation
    // from OS
    for (auto it = body.begin(), end = body.end(); it != end; ++it) {
        head_part /= ReadBaseNameWithCase(head_part / *it);
    }

    return head_part;
}

// Find out if input param contains any of the glob patterns **, * or ?.
//
// return               An enumeration value: None if no glob pattern
//                                            Simple if * or ?
//                                            Recursive if **
GlobType DetermineGlobType(const std::wstring &Input) {
    const std::wstring patterns[] = {
        {L"^\\*\\*$"},  // "**"
        {L".*\\*.*"},   // "anything*anything"
        {L".*\\?.*"}    // "anything?anything"
    };

    std::wsmatch match;
    try {
        if (std::regex_match(Input, match, std::wregex(patterns[0])))
            return GlobType::kRecursive;
        if (std::regex_match(Input, match, std::wregex(patterns[1])) ||
            std::regex_match(Input, match, std::wregex(patterns[2])))
            return GlobType::kSimple;
    } catch (const std::exception &e) {
        XLOG::l("Bad pattern {} '{}'", wtools::ConvertToUTF8(Input), e.what());
    } catch (...) {
        XLOG::l.crit("Bad pattern {} '{}'", wtools::ConvertToUTF8(Input));
    }

    return GlobType::kNone;
}

// Recursive scan, gather ALL FILES that match file pattern
// and adds(!) them to input parameter
// Search path is starting point for recursive search
// File pattern is original value from yaml.fileinfo.path[n]
void GatherMatchingFilesRecursive(const std::filesystem::path &SearchPath,
                                  const std::filesystem::path &FilePattern,
                                  PathVector &Files) noexcept {
    namespace fs = std::filesystem;

    try {
        for (const auto &entry : fs::recursive_directory_iterator(
                 SearchPath, fs::directory_options::skip_permission_denied)) {
            // Found files must match the entire path pattern.
            std::error_code ec;
            auto status = entry.status(ec);
            auto entry_name = entry.path();
            if (ec) {
                XLOG::t("Access to {} is not possible, status {}",
                        entry_name.u8string(), ec.value());
                continue;
            }

            if (!fs::is_regular_file(status)) continue;

            // normal file
            if (cma::tools::GlobMatch(FilePattern.wstring(),
                                      entry_name.wstring()))  // mask match
            {
                Files.push_back(entry);
            }
        }
    } catch (std::exception &e) {
        XLOG::l("Exception recursive {}", e.what());
    } catch (...) {
        XLOG::l("Exception recursive");
    }
}

// Scan one folder and add contents to the dirs and files
void GatherMatchingFilesAndDirs(
    const std::filesystem::path &SearchDir,    // c:\windows
    const std::filesystem::path &DirPattern,   // c:\windows\L*
    const std::filesystem::path &FilePattern,  // c:\windows\L*\*.log
    PathVector &FilesFound,                    // output
    PathVector &DirsFound) {                   // output
    namespace fs = std::filesystem;
    for (const auto &p : fs::directory_iterator(SearchDir)) {
        // Found files must match the entire path pattern.
        std::error_code ec;
        auto status = p.status();  // CMK-1417, to be confirmed in ticket
        if (ec) {                  // ! error
            XLOG::d("Cant obtain status for dir {} path {}status is {}",
                    SearchDir.u8string(), p.path().u8string(), ec.value());
            continue;
        }

        auto path = p.path();
        // normal file
        if (fs::is_regular_file(status) &&
            cma::tools::GlobMatch(FilePattern.wstring(), path.wstring())) {
            FilesFound.push_back(path);
            continue;
        }

        // directory
        if (fs::is_directory(status) &&
            cma::tools::GlobMatch(DirPattern.wstring(), path.wstring())) {
            DirsFound.push_back(path);
            continue;
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
    const PathVector &DirsToSearch,
    const std::filesystem::path &PatternToUse,  //
    const std::filesystem::path &Mask) {
    PathVector files;
    PathVector dirs;
    for (const auto &dir : DirsToSearch) {
        auto pattern_to_check = dir / PatternToUse;
        GatherMatchingFilesAndDirs(dir, pattern_to_check, Mask, files, dirs);
    }

    return {files, dirs};
}

//
// Find files and directories in the dir
//
PathVector FindFilesAndDirsInSubdirRecursive(
    const PathVector &DirsToSearch, const std::filesystem::path &Mask) {
    PathVector files;
    for (const auto &dir : DirsToSearch) {
        GatherMatchingFilesRecursive(dir, Mask, files);
    }

    return files;
}

// Gets all dirs add Change => to get path array
// clean Dirs!
// if path is dir add to Dirs
// if path is file add to Files
static void ProcessDirsAndFilesTables(PathVector &Dirs, PathVector &Files,
                                      std::filesystem::path Change) {
    namespace fs = std::filesystem;

    // update dirs table with "Change"
    for (auto &entry : Dirs) entry /= Change;

    // check what the hell we have in Dirs and update Files
    for (auto &entry : Dirs) {
        std::error_code ec;
        auto good_file = fs::is_regular_file(entry, ec);
        if (ec) {  // not found, reporting only when error is serious
            if (ec.value() != 2) {  // 2 means NOT FOUND, this is ok
                // low probability. Something really bad
                XLOG::t("Cant access file {} status {}", entry.u8string(),
                        ec.value());
            }
            continue;
        }

        // no error
        if (good_file) {
            // good boy found, push it the files
            Files.push_back(entry);
        }
    }

    // remove non-dirs entry form dirs table
    auto last_pos =
        std::remove_if(Dirs.begin(), Dirs.end(), [](fs::path &Path) {
            std::error_code ec;
            auto is_dir = fs::is_directory(Path, ec);
            if (!ec)             // no error
                return !is_dir;  // remove all what is not dir

            if (ec.value() != 2) {
                // we write warning only for bad access writes and so on
                // not found in this case acceptable
                XLOG::d("Suspicious dir {} status {}", Path.u8string(),
                        ec.value());
            }
            return true;  // remove trash with error too
        });

    // C++ feature: we don't want move to much
    Dirs.erase(last_pos, Dirs.end());
}

static void AddVectorWithMove(PathVector &Files, PathVector &FoundFiles) {
    Files.reserve(Files.size() + FoundFiles.size());
    std::copy(std::move_iterator(FoundFiles.begin()),
              std::move_iterator(FoundFiles.end()), std::back_inserter(Files));
}

// gtested internally
PathVector FindFileBySplittedPath(const std::filesystem::path &Head,  // c:\ 
                                  const std::filesystem::path &Body, // path
                                  const std ::wstring &Mask) {  // c:\x\*x.txt
    // output storages:
    PathVector dirs = {Head};
    PathVector files;

    // Code below is verified and modified code from legacy agent
    // Iterate through the path element per element
    // c:\a\b\c\d => for c:\, a, b, c, d ....
    // we checking for a, b, c, d contains glob.
    // If contains, then we scan for all inside
    // If not, we just update our lists, dirs & files
    auto end = Body.end();
    for (auto it = Body.begin(); it != end; ++it) {
        // check element of path on pattern:
        auto globType = details::DetermineGlobType(it->wstring());

        // no pattern, just add to all dirs we have
        if (globType == GlobType::kNone) {
            ProcessDirsAndFilesTables(dirs, files, *it);
            continue;
        }

        // trivial case
        if (globType == GlobType::kSimple) {
            auto [found_files, found_dirs] =
                FindFilesAndDirsInSubdir(dirs, *it, Mask);
            // add files to table
            AddVectorWithMove(files, found_files);

            // replace(!) dir table
            dirs = std::move(found_dirs);
            continue;
        }

        // For recursive glob, the rest of the path was already traversed.
        auto found_files = FindFilesAndDirsInSubdirRecursive(dirs, Mask);

        // add files to table
        AddVectorWithMove(files, found_files);
        break;
    }

    std::sort(files.begin(), files.end());

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

PathVector FindFilesByMask(const std::wstring Mask) {
    namespace fs = std::filesystem;

    // Trivial case, standard file, just return it back
    std::error_code ec;
    if (fs::is_regular_file(Mask, ec)) {
        XLOG::t("Found regular file as path {}", wtools::ConvertToUTF8(Mask));
        return {fs::path(Mask)};
    }

    // Split path in root and body part
    auto [head_out, body_out] = details::SplitFileInfoPathSmart(Mask);
    if (head_out.u8string().empty() || body_out.u8string().empty()) {
        return {};
    }

    // no error code checking here - Mask may contain a pattern
    return FindFileBySplittedPath(head_out, body_out, Mask);
}

bool ValidFileInfoPathEntry(const std::string Entry) {
    namespace fs = std::filesystem;
    if (Entry.empty()) return false;

    fs::path p = wtools::ConvertToUTF16(Entry);
    if (p.root_name().empty()) return false;

    if (p.root_directory().empty()) return false;

    return true;
}

// returns UTF8
std::string MakeFileInfoString(const std::filesystem::path &FilePath) {
    namespace fs = std::filesystem;
    using namespace std;
    // strange dances from legacy agent
    // const auto finalPath = correctPathCase(FilePath, winapi);
    std::error_code ec;
    auto file_size = fs::file_size(FilePath, ec);
    if (ec) {
        XLOG::l.e("Cant get size of file {}  status {}", FilePath.u8string(),
                  ec.value());
        file_size = 0;
    }

    int64_t seconds = 0;
    auto file_last_touch = fs::last_write_time(FilePath, ec);
    if (ec) {
        XLOG::l.e("Cant get las touch of file {} status {}",
                  FilePath.u8string(), ec.value());
        seconds = 0;
    } else {
        auto duration = chrono::duration_cast<chrono::seconds>(
            file_last_touch.time_since_epoch());
        seconds = duration.count();
    }
    auto file_name = GetOsPathWithCase(FilePath);
    return fmt::format("{}|{}|{}\n", file_name.u8string(), file_size, seconds);
}

// single entry form config
// path =
std::string ProcessFileInfoPathEntry(const std::string Entry) {
    // this is MUST
    std::wstring mask = wtools::ConvertToUTF16(Entry);

    const auto filePaths = FindFilesByMask(mask);

    if (filePaths.empty()) {
        return wtools::ConvertToUTF8(
            mask + L"|missing|" +
            std::to_wstring(cma::tools::SecondsSinceEpoch()) + L"\n");
    }

    std::string out;
    for (const auto &entry : filePaths) {
        out += MakeFileInfoString(entry);
    }

    return out;
}

}  // namespace cma::provider::details

namespace cma {

namespace provider {

void FileInfo::loadConfig() {}

// #TODO still not gtested directly
// return array of path's if can otherwise nothing
std::optional<YAML::Node> GetPathArray() noexcept {
    using namespace cma::cfg;
    const auto cfg = cma::cfg::GetLoadedConfig();
    try {
        const auto finfo_section = cfg[groups::kFileInfo];

        // sanity checks:
        if (!finfo_section) {
            XLOG::t("'{}' section absent", groups::kFileInfo);
            return {};
        }

        if (!finfo_section.IsMap()) {
            XLOG::l("'{}' is not correct", groups::kFileInfo);
            return {};
        }

        // get array, on success, return it
        const auto path_array = finfo_section[vars::kFileInfoPath];
        if (!path_array) {
            XLOG::t("'{}' section has no '{}' member", groups::kFileInfo,
                    vars::kFileInfoPath);
            return {};
        }

        if (!path_array.IsSequence()) {
            XLOG::l("'{}.{}' malformed", groups::kFileInfo,
                    vars::kFileInfoPath);
            return {};
        }

        return path_array;
    } catch (const std::exception &e) {
        XLOG::l(
            "CONFIG for '{}.{}' is seriously not valid, skipping. Exception {}",
            groups::kFileInfo, vars::kFileInfoPath, e.what());
        return {};
    }
}

std::string FileInfo::makeBody() const {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    // mandatory part of the output:
    auto time_in = std::to_string(cma::tools::SecondsSinceEpoch());
    std::string out = time_in + "\n";

    // optional part of the output:
    // #TODO rethink move to loadConfig
    auto path_array_val = GetPathArray();
    if (!path_array_val.has_value()) return out;

    int i_pos = 0;
    auto path_array = path_array_val.value();
    for (auto it = path_array.begin(); it != path_array.end(); ++it) {
        try {
            auto mask = it->as<std::string>();

            if (details::ValidFileInfoPathEntry(mask)) {
                //
                out += details::ProcessFileInfoPathEntry(mask);
            } else {
                XLOG::l.t("'{}.{}[{}] = {}' is not valid, skipping",
                          groups::kFileInfo, vars::kFileInfoPath, i_pos, mask);
            }

        } catch (const std::exception &e) {
            XLOG::l(
                "'{}.{}[{}]' is seriously not valid, skipping. Exception {}",
                groups::kFileInfo, vars::kFileInfoPath, i_pos, e.what());
        }
        i_pos++;
    }

    return out;
}

}  // namespace provider
};  // namespace cma
