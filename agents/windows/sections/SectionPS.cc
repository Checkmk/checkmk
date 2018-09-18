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

#include "SectionPS.h"
#include <iomanip>
#include "Environment.h"
#include "Logger.h"
#include "PerfCounter.h"
#include "SectionHeader.h"
#include "dynamic_func.h"
#include "win_error.h"

namespace {

const unsigned long long SEC_TO_UNIX_EPOCH = 11644473600L;
const unsigned long WINDOWS_TICK = 10000000;

inline unsigned long long sinceEpoch(const FILETIME &filetime) {
    ULARGE_INTEGER uli{0};
    uli.LowPart = filetime.dwLowDateTime;
    uli.HighPart = filetime.dwHighDateTime;

    return uli.QuadPart / WINDOWS_TICK - SEC_TO_UNIX_EPOCH;
}

}  // namespace

SectionPS::SectionPS(Configuration &config, Logger *logger,
                     const WinApiInterface &winapi)
    : Section(
          "ps", config.getEnvironment(), logger, winapi,
          std::make_unique<SectionHeader<'\t', SectionBrackets>>("ps", logger))
    , _use_wmi(config, "ps", "use_wmi", true, winapi)
    , _full_commandline(config, "ps", "full_path", false, winapi) {}

SectionPS::process_entry_t SectionPS::getProcessPerfdata() {
    process_entry_t process_info;

    unsigned processBaseNumber = 230;
    PerfCounterObject counterObject(processBaseNumber, _winapi, _logger);

    if (!counterObject.isEmpty()) {
        LARGE_INTEGER Frequency;
        _winapi.QueryPerformanceFrequency(&Frequency);

        std::vector<PERF_INSTANCE_DEFINITION *> instances =
            counterObject.instances();

        std::vector<process_entry> entries(
            instances.size());  // one instance = one process

        // gather counters
        for (const PerfCounter &counter : counterObject.counters()) {
            std::vector<ULONGLONG> values = counter.values(instances);
            for (std::size_t i = 0; i < values.size(); ++i) {
                switch (counter.offset()) {
                    case 40:
                        entries.at(i).virtual_size = values[i];
                        break;
                    case 56:
                        entries.at(i).working_set_size = values[i];
                        break;
                    case 64:
                        entries.at(i).pagefile_usage = values[i];
                        break;
                    case 104:
                        entries.at(i).process_id = values[i];
                        break;
                }
            }
        }

        for (const process_entry &entry : entries) {
            process_info[entry.process_id] = entry;
        }
    }
    return process_info;
}

bool SectionPS::ExtractProcessOwner(const NullHandle &hProcess_i,
                                    std::string &csOwner_o) {
    // Get process token
    HANDLE rawHandle = INVALID_HANDLE_VALUE;

    if (!_winapi.OpenProcessToken(hProcess_i.get(), TOKEN_READ, &rawHandle)) {
        return false;
    }

    WinHandle hProcessToken{rawHandle, _winapi};

    if (!hProcessToken) {
        return false;
    }

    // First get size needed, TokenUser indicates we want user information from
    // given token
    DWORD dwProcessTokenInfoAllocSize = 0;
    _winapi.GetTokenInformation(hProcessToken.get(), TokenUser, NULL, 0,
                                &dwProcessTokenInfoAllocSize);

    // Call should have failed due to zero-length buffer.
    if (_winapi.GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
        // Allocate buffer for user information in the token.
        std::vector<unsigned char> UserToken(dwProcessTokenInfoAllocSize, 0);
        PTOKEN_USER pUserToken =
            reinterpret_cast<PTOKEN_USER>(UserToken.data());
        // Now get user information in the allocated buffer
        if (_winapi.GetTokenInformation(hProcessToken.get(), TokenUser,
                                        pUserToken, dwProcessTokenInfoAllocSize,
                                        &dwProcessTokenInfoAllocSize)) {
            // Some vars that we may need
            SID_NAME_USE snuSIDNameUse;
            WCHAR szUser[MAX_PATH] = {0};
            DWORD dwUserNameLength = MAX_PATH;
            WCHAR szDomain[MAX_PATH] = {0};
            DWORD dwDomainNameLength = MAX_PATH;

            // Retrieve user name and domain name based on user's SID.
            if (_winapi.LookupAccountSidW(
                    NULL, pUserToken->User.Sid, szUser, &dwUserNameLength,
                    szDomain, &dwDomainNameLength, &snuSIDNameUse)) {
                csOwner_o = "\\\\" + to_utf8(szDomain) + "\\" + to_utf8(szUser);
                return true;
            }
        }
    }
    return false;
}

bool SectionPS::produceOutputInner(std::ostream &out,
                                   const std::optional<std::string> &) {
    Debug(_logger) << "SectionPS::produceOutputInner";
    if (*_use_wmi) {
        return outputWMI(out);
    } else {
        return outputNative(out);
    }
}

void SectionPS::outputProcess(std::ostream &out, ULONGLONG virtual_size,
                              ULONGLONG working_set_size,
                              long long pagefile_usage, ULONGLONG uptime,
                              long long usermode_time,
                              long long kernelmode_time, long long process_id,
                              long long process_handle_count,
                              long long thread_count, const std::string &user,
                              const std::string &exe_file) {
    // Note: CPU utilization is determined out of usermodetime and
    // kernelmodetime
    out << "(" << user << "," << virtual_size / 1024 << ","
        << working_set_size / 1024 << ",0"
        << "," << process_id << "," << pagefile_usage / 1024 << ","
        << usermode_time << "," << kernelmode_time << ","
        << process_handle_count << "," << thread_count << "," << uptime << ")\t"
        << exe_file << "\n";
}

bool SectionPS::outputWMI(std::ostream &out) {
    Debug(_logger) << "SectionPS::ouputWMI";
    if (_helper.get() == nullptr) {
        _helper.reset(new wmi::Helper(_logger, _winapi, L"Root\\cimv2"));
    }

    wmi::Result result(_logger, _winapi);
    try {
        result = _helper->getClass(L"Win32_Process");
        bool more = result.valid();

        while (more) {
            long long processId = result.get<long long>(L"ProcessId");

            NullHandle process(
                _winapi.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                    FALSE, processId),
                _winapi);
            std::string user = "SYSTEM";
            ExtractProcessOwner(process, user);
            std::wstring process_name;

            if (*_full_commandline && result.contains(L"ExecutablePath")) {
                process_name = result.get<std::wstring>(L"ExecutablePath");
            } else {
                process_name = result.get<std::wstring>(L"Caption");
            }

            if (*_full_commandline && result.contains(L"CommandLine")) {
                int argc;
                LocalMemoryHandle<LPWSTR *> argv(
                    _winapi.CommandLineToArgvW(
                        result.get<std::wstring>(L"CommandLine").c_str(),
                        &argc),
                    _winapi);
                for (int i = 1; i < argc; ++i) {
                    process_name += std::wstring(L" ") + argv.get()[i];
                }
            }

            auto creation_date = result.get<std::wstring>(L"CreationDate");
            std::wistringstream ss(creation_date);
            std::tm t;
            ss >> std::get_time(&t, L"%Y%m%d%H%M%S");
            time_t creation_time = mktime(&t);
            // Cope with possible problems with process creation time. Ensure
            // that the result of subtraction is not negative.
            long long currTime = section_helpers::current_time();
            long long timeDiff = currTime - creation_time;

            if (timeDiff < 0) {
                Error(_logger) << "Creation time " << creation_time
                               << " lies ahead of current time " << currTime;
            }

            auto uptime = static_cast<ULONGLONG>(std::max(timeDiff, 1LL));

            outputProcess(
                out, std::stoull(result.get<std::string>(L"VirtualSize")),
                std::stoull(result.get<std::string>(L"WorkingSetSize")),
                result.get<long long>(L"PagefileUsage"), uptime,
                std::stoull(result.get<std::wstring>(L"UserModeTime")),
                std::stoull(result.get<std::wstring>(L"KernelModeTime")),
                processId, result.get<long long>(L"HandleCount"),
                result.get<long long>(L"ThreadCount"), user,
                to_utf8(process_name));

            more = result.next();
        }
        return true;
    } catch (const wmi::ComException &e) {
        // the most likely cause is that the wmi query fails, i.e. because the
        // service is currently offline.
        Error(_logger) << "ComException: " << e.what();
    } catch (const wmi::ComTypeException &e) {
        Error(_logger) << "ComTypeException: " << e.what();
        std::wstring types;
        std::vector<std::wstring> names;
        for (std::vector<std::wstring>::const_iterator iter = names.begin();
             iter != names.end(); ++iter) {
            types += *iter + L"=" +
                     std::to_wstring(result.typeId(iter->c_str())) + L", ";
        }
        Error(_logger)
            << "Data types are different than expected, please report this and "
            << "include the following: " << Utf8(types);
    }
    return false;
}

bool SectionPS::outputNative(std::ostream &out) {
    Debug(_logger) << "SectionPS::ouputNative";
    PROCESSENTRY32 pe32{0};

    process_entry_t process_perfdata;
    try {
        process_perfdata = getProcessPerfdata();
    } catch (const std::runtime_error &e) {
        // the most likely cause is that the wmi query fails, i.e. because the
        // service is currently offline.
        Error(_logger) << "Exception: Error while querying process perfdata: "
                       << e.what();
    }

    WinHandle hProcessSnap{
        _winapi.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0), _winapi};
    if (!hProcessSnap) {
        return false;
    }
    pe32.dwSize = sizeof(PROCESSENTRY32);

    bool more = _winapi.Process32First(hProcessSnap.get(), &pe32);

    // GetProcessHandleCount is only available winxp upwards
    using GetProcessHandleCount_type = BOOL WINAPI (*)(HANDLE, PDWORD);
    LPCWSTR dllName = L"kernel32.dll";
    LPCSTR funcName = "GetProcessHandleCount";
    GetProcessHandleCount_type GetProcessHandleCount_dyn =
        dynamic_func<GetProcessHandleCount_type>(dllName, funcName, _winapi);

    while (more) {
        std::string user = "unknown";
        DWORD dwAccess = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
        NullHandle hProcess{
            _winapi.OpenProcess(dwAccess, FALSE, pe32.th32ProcessID), _winapi};

        // TODO the following isn't really necessary. We need the process
        // handle only to determine process owner and handle count,
        // the process list could still be useful without that.
        if (hProcess) {
            // Process times
            FILETIME createTime, exitTime, kernelTime, userTime;
            ULARGE_INTEGER kernelmodetime, usermodetime;
            if (_winapi.GetProcessTimes(hProcess.get(), &createTime, &exitTime,
                                        &kernelTime, &userTime) != 0) {
                kernelmodetime.LowPart = kernelTime.dwLowDateTime;
                kernelmodetime.HighPart = kernelTime.dwHighDateTime;
                usermodetime.LowPart = userTime.dwLowDateTime;
                usermodetime.HighPart = userTime.dwHighDateTime;
            } else {
                Error(_logger) << "GetProcessTimes failed: "
                               << get_win_error_as_string(_winapi);
            }

            DWORD processHandleCount = 0;

            if (GetProcessHandleCount_dyn != nullptr) {
                GetProcessHandleCount_dyn(hProcess.get(), &processHandleCount);
            }

            // Process owner
            ExtractProcessOwner(hProcess, user);

            // Memory levels
            ULONGLONG working_set_size = 0;
            ULONGLONG virtual_size = 0;
            ULONGLONG pagefile_usage = 0;
            process_entry_t::iterator it_perf =
                process_perfdata.find(pe32.th32ProcessID);
            if (it_perf != process_perfdata.end()) {
                working_set_size = it_perf->second.working_set_size;
                virtual_size = it_perf->second.virtual_size;
                pagefile_usage = it_perf->second.pagefile_usage;
            }

            // Uptime
            // Cope with possible problems with process creation time. Ensure
            // that the result of subtraction is not negative.
            long long currTime = section_helpers::current_time();
            long long timeDiff = currTime - sinceEpoch(createTime);

            if (timeDiff < 0) {
                Error(_logger) << "Creation time " << sinceEpoch(createTime)
                               << " lies ahead of current time " << currTime;
            }

            auto uptime =
                static_cast<unsigned long long>(std::max(timeDiff, 1LL));

            // Note: CPU utilization is determined out of usermodetime and
            // kernelmodetime
            outputProcess(out, virtual_size, working_set_size, pagefile_usage,
                          uptime, usermodetime.QuadPart,
                          kernelmodetime.QuadPart, pe32.th32ProcessID,
                          processHandleCount, pe32.cntThreads, user,
                          pe32.szExeFile);
        } else {
            Error(_logger) << "SectionPS::outputNative: OpenProcess failed";
        }
        more = _winapi.Process32Next(hProcessSnap.get(), &pe32);
    }
    process_perfdata.clear();

    // The process snapshot doesn't show the system idle process (used to
    // determine the number of cpu cores)
    // We simply fake this entry..
    SYSTEM_INFO sysinfo;
    _winapi.GetSystemInfo(&sysinfo);
    outputProcess(out, 0, 0, 0, 0, 0, 0, 0, 0, sysinfo.dwNumberOfProcessors,
                  "SYSTEM", "System Idle Process");
    return true;
}
