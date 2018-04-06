// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

#ifndef WritableFile_h
#define WritableFile_h

#include <unordered_set>
#include "types.h"

class Environment;

class FileError : public std::runtime_error {
public:
    FileError(const std::string &path, const std::string &what)
        : std::runtime_error(constructMessage(path, what)) {}

private:
    std::string constructMessage(const std::string &path,
                                 const std::string &what) const;
};

class WritableFile {
public:
    /**
     * Open file in given path for writing. File is closed when the constructed
     * instance goes out of scope.
     *
     * @param[in] filePath    The path to the file to be opened
     * @param[in] shareMode   The sharing mode (see WinAPI CreateFile)
     * @param[in] disposition The action with [non-]existing file (->CreateFile)
     * @param[in] winapi      Reference to the WinAPI interface to be used
     * @throw FileError       If a writable file cannot be created or opened
     *                        (WinAPI CreateFile fails)
     *
     */
    WritableFile(const std::string &filePath, DWORD shareMode,
                 DWORD disposition, const WinApiInterface &winapi);

    WritableFile(const WritableFile &) = delete;
    WritableFile &operator=(const WritableFile &) = delete;

    /**
     * Write given string to file.
     *
     * @param[in] s        String to be written
     * @throw FileError    If the write operation fails
     */
    WritableFile &operator<<(const std::string &s);

    /**
     * Write given byte sequence to file.
     *
     * @param[in] s        Byte sequence to be written
     * @throw FileError    If the write operation fails
     */
    WritableFile &operator<<(const std::vector<BYTE> &s);

private:
    const std::string _path;
    WrappedHandle<InvalidHandleTraits> _hFile;
    const WinApiInterface &_winapi;
};

/**
 * Get list of default files to be excluded from areAllFilesWritable.
 *
 * @param[in] env        Reference to the global environment
 * @param[in] winapi     Reference to the WinAPI interface to be used
 * @return               unordered_set of absolute file paths.
 */
std::unordered_set<std::string> getDefaultWhitelist(
    const Environment &env, const WinApiInterface &winapi);

/**
 * Check recursively that the current user has write permissions to each file in
 * given directory path. Throws FileError at first file that is lacking write
 * permissions.
 *
 * @param[in] dirPath    The directory path to be checked recursively
 * @param[in] winapi     Reference to the WinAPI interface to be used
 * @param[in] whitelist  Files (full path!) to be excluded, default: empty
 * @return               true if all files are writable
 * @throw FileError      At first non-writable file
 */
bool areAllFilesWritable(const std::string &dirPath,
                         const WinApiInterface &winapi,
                         const std::unordered_set<std::string> &whitelist = {});

#endif  // WritableFile_h
