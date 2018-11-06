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

// SK: Simple Functions to find executable and run them
// Fully Tested with GTEST
/*
Usage:
    #include "ModuleControl.h"

    // finding
    using namespace cma;
    std::string paths[] = { path1, cma::wnd::kUtilsFolder, path2 };
    std::string exe(cma::wnd::kPerfReaderExe);
    for ( auto& path : paths)
    {
        auto full_path = FindModule( path, exe);
        if (full_path[0])
        {
            break;
        }
    }

    // reading
    auto fname = cma::BuildTmpProcIdFileName( L"510" ); // make tmp file
    auto result = cma::RunModule(L"path/to/perfreader", fname + L" " + counter);
    //read file
    auto data_block = cma::ReadFile(fname.c_str());

    //
    DeleteFile(fname.c_str());

*/

#pragma once

#define WINDOWS_LEAN_AND_MEAN
#include <windows.h>
#include <sys/stat.h>
#include <string>
#include <fstream>
#include <cstdint>

// MAIN NAMESPACE for C++ based Check MK Agents
namespace cma {
namespace wnd {
// well-known names
const wchar_t* const kPluginsFolder = L"plugins";
const wchar_t* const kUtilsFolder = L"local";
const wchar_t* const kLocalFolder = L"utils";
const wchar_t* const kPerfReaderExe = L"perf_reader.exe";
namespace test {
const wchar_t* const kPlugin = L"plugin_tmp.exe";
const wchar_t* const kUtil = L"local_tmp.exe";
const wchar_t* const kLocal = L"util_tmp.exe";
}  // namespace test
}  // namespace wnd

// private:
inline void AddConditionallySlash(std::string& Value) {
    if (Value.back() == '\\' || Value.back() == '/')
        ;  // ok
    else {
        Value += '/';
    }
}

// private:
inline void AddConditionallySlash(std::wstring& Value) {
    if (Value.back() == L'\\' || Value.back() == L'/')
        ;  // ok
    else {
        Value += L'/';
    }
}

template <typename T>
std::basic_string<T> MakeFullPath(const std::basic_string<T>& Folder,
                                  const std::basic_string<T>& Name) {
    if (!Name[0]) return std::basic_string<T>();

    std::basic_string<T> full_path = Folder;
    if (full_path[0]) {
        AddConditionallySlash(full_path);
    }
    full_path += Name;

    return full_path;
}

template <typename T>
std::basic_string<T> MakeFullPath(const T* Folder, const T* Name) {
    return MakeFullPath(std::basic_string<T>(Folder),
                        std::basic_string<T>(Name));
}

template <typename T>
bool IsFileExist(const std::basic_string<T>& Name) {
#if defined(_MSC_BUILD)
    std::ifstream f(Name.c_str());
#else
    // GCC can't unicode, conversion required
    std::string file_name(Name.begin(), Name.end());
    std::ifstream f(file_name.c_str());
#endif
    return f.good();
}

// FIND MODULE
// returns valid full path to module if ModuleName exists on relative folder
// path
template <typename T>
std::basic_string<T> FindModule(const std::basic_string<T>& RelativePath,
                                const std::basic_string<T>& ModuleName) {
    auto full_path = MakeFullPath<T>(RelativePath, ModuleName);
    if (full_path[0])
        return IsFileExist(full_path) ? full_path : std::basic_string<T>();
    else
        return std::basic_string<T>();
}

template <typename T>
std::basic_string<T> FindModule(const T* Folder, const T* Name) {
    return FindModule(std::basic_string<T>(Folder), std::basic_string<T>(Name));
}

// only UNICODE
inline bool RunModule(const std::wstring& ApplicationName,
                      const std::wstring& CommandLine, bool Test = false) {
    STARTUPINFOW si{0};
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags |= STARTF_USESTDHANDLES;  // SK: not sure with this flag

    PROCESS_INFORMATION pi{0};
    memset(&pi, 0, sizeof(pi));
    // CREATE_NEW_CONSOLE

    if (::CreateProcessW(
            NULL,  // stupid windows want null here
            (wchar_t*)(L"\"" + ApplicationName + L"\" " + CommandLine).c_str(),
            nullptr, nullptr, TRUE, 0, nullptr, nullptr, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);

        return true;
    }

    if (Test)
        printf("Error during process creation %u\n", (uint32_t)GetLastError());

    return false;
}

// returns empty string when failed
inline std::wstring BuildTmpProcIdFileName(const std::wstring& CounterName) {
    constexpr int sz = 512;
    constexpr const wchar_t* kWinTemp = L"TEMP";

    wchar_t temp_folder[sz] = {0};
    GetEnvironmentVariableW(kWinTemp, temp_folder, sz - 1);
    if (temp_folder[0]) {
        std::wstring full_path = temp_folder;
        full_path += L"/out_" + std::to_wstring(GetCurrentProcessId()) + L"_";
        full_path += CounterName;
        return full_path;
    } else {
        return std::wstring();
    }
}

// simple storage for data, raw pointer + length
struct DataBlock {
    // default and normal CTOR
    DataBlock() : len_(0), data_(nullptr) {}
    DataBlock(int Size, char* Buffer) : len_(Size), data_(Buffer) {}
    ~DataBlock() { delete[] data_; }

    // no copy:
    DataBlock(const DataBlock&) = delete;
    DataBlock& operator=(const DataBlock&) = delete;

    // move:
    DataBlock(DataBlock&& Rhs) {
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
    }

    DataBlock& operator=(DataBlock&& Rhs) {
        data_ = Rhs.data_;
        len_ = Rhs.len_;
        Rhs.data_ = nullptr;
        Rhs.len_ = 0;
        return *this;
    }

    // data
    int len_;
    char* data_;
};

template <typename T>
DataBlock ReadFile(const T* FileName) {
    try {
#if defined(_MSC_BUILD)
        std::ifstream f(FileName, std::ios::binary);
#else
        // GCC can't wchar, conversion required
        std::basic_string<T> str(FileName);
        std::string file_name(str.begin(), str.end());
        std::ifstream f(file_name, std::ios::binary);
#endif

        if (!f.good()) return DataBlock();

        // size obtain
        f.seekg(0, std::ios::end);
        auto fsize = static_cast<uint32_t>(f.tellg());

        // buffer obtain
        char* buffer = nullptr;
        buffer = new char[fsize];

        // read contents
        f.seekg(0, std::ios::beg);
        f.read(buffer, fsize);

        f.close();  // normally not required, closed automatically
        return DataBlock(static_cast<int>(fsize), buffer);
    } catch (...) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        return DataBlock();
    }
    return DataBlock();
}

};  // namespace cma
