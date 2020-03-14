// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// ONLY SELF TESTING(no google test)
// USED to read data from the registry and avoid handle leaking
// WIndows NON PORTABLE
// Code is not 1005 clear due to simplicity

#include "pch.h"
#if !defined(_MSC_BUILD)
#error "Visual Studio required!"
#endif

#include <fcntl.h>
#include <io.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "tools/_raii.h"

static const wchar_t* kTestOutputFile = L"test_output_file.tmp";
static const wchar_t* kTestCountersName = L"510";

// supplementary structure to store data
struct DataBlock {
    DataBlock() : len_(0), data_(nullptr) {}
    DataBlock(int Size, BYTE* Buffer) : len_(Size), data_(Buffer) {}
    ~DataBlock() { delete[] data_; }

    // no copy:
    DataBlock(const DataBlock&) = delete;
    DataBlock& operator=(const DataBlock&) = delete;

    // default move
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
    }

    int len_;
    BYTE* data_;
};

// copy from the check_mk_agent windows
static DataBlock ReadPerformanceDataFromRegistry(const wchar_t* CounterList) {
    DWORD type = 0;

    DWORD buf_size = 40000;
    BYTE* buffer = nullptr;

    while (1) {
        // allocation(a bit stupid, but we do not want top have STL inside
        try {
            buffer = new BYTE[buf_size];
        } catch (...) {
            return DataBlock();  // ups
        }

        auto ret = ::RegQueryValueExW(HKEY_PERFORMANCE_DATA, CounterList,
                                      nullptr, &type, buffer, &buf_size);
        RegCloseKey(HKEY_PERFORMANCE_DATA);  // MSDN requirement

        if (ret == ERROR_SUCCESS) break;  // normal exit

        if (ret == ERROR_MORE_DATA) {
            buf_size *= 2;  // :)
            delete buffer;  // realloc part one
            continue;       // to be safe
        } else
            return DataBlock();
    }

    return DataBlock((int)buf_size, buffer);
}

// **** main function *******
// If FileName == nullptr, then no write to file
// returns 0 - if all ok
// last error or 100x
static int RunEngine(const wchar_t* FileName, const wchar_t* CounterList,
                     bool Test) {
    // READ COUNTER
    auto counter_list = CounterList;
    auto result = ReadPerformanceDataFromRegistry(counter_list);
    if (!result.data_) {
        return 1001;
    }

    auto block = reinterpret_cast<PERF_DATA_BLOCK*>(result.data_);

    if (!wcscmp(block->Signature, L"PERF")) {
        if (Test) printf("Counter returns bad signature %ws", block->Signature);
        return 1002;
    }

    // File Name check
    auto fname = FileName;
    if (fname == nullptr) return 0;  // ok

    auto len = wcslen(fname);
    if (len < 2) {
        if (Test) printf("FileName %ws too short", FileName);
        return 1003;
    }

    // OPEN FILE
    auto fh = _wopen(FileName, O_CREAT | O_BINARY | O_TRUNC | O_RDWR,
                     _S_IWRITE | _S_IREAD);
    if (fh == 0 || fh == -1) {
        return 1003;
    }
    ON_OUT_OF_SCOPE(_close(fh););

    // WRITE to FILE
    auto ret = _write(fh, result.data_, result.len_);
    if (ret != result.len_) {
        auto last_error = GetLastError();
        if (Test)
            printf("Failed write file %ws to open %d", FileName, last_error);
        return last_error;
    }

    return 0;
}

static int RunHelp() {
    printf(
        "Usage:\n"
        "%s <filename> <counterlist>\n"
        "%s test\n"
        "%s test <filename> <counterlist>\n"
        "%s help\n",
        OUTPUT_EXE_NAME, OUTPUT_EXE_NAME, OUTPUT_EXE_NAME,
        OUTPUT_EXE_NAME  // defined in solution
    );
    return 0;
}

int wmain(int Argc, wchar_t** Argv) {
    // parameters check for special command options
    if (Argc == 2 || Argc == 4) {
        if (0 == wcscmp(Argv[1], L"test")) {
            if (Argc == 2)
                return RunEngine(kTestOutputFile, kTestCountersName, true);
            else
                return RunEngine(Argv[2], Argv[3], true);
        }

        return RunHelp();
    }

    // last check
    if (Argc != 3) {
        RunHelp();
        return 1;
    }

    // normal execution
    return RunEngine(Argv[1], Argv[2], false);
}
