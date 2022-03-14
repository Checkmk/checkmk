// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#if defined(_WIN32)
#include <shellapi.h>
#endif

#include <ranges>
#include <string>
#include <tuple>

#include "cfg.h"
#include "common/wtools.h"
#include "logger.h"
#include "providers/ps.h"
#include "providers/wmi.h"
#include "tools/_raii.h"
#include "tools/_win.h"

namespace cma::provider {

// Process Line Formatter
// not static to be fully tested by unit tests
std::string OutputProcessLine(ULONGLONG virtual_size,
                              ULONGLONG working_set_size,
                              long long pagefile_usage, ULONGLONG uptime,
                              long long usermode_time,
                              long long kernelmode_time, long long process_id,
                              long long process_handle_count,
                              long long thread_count, const std::string &user,
                              const std::string &exe_file) {
    auto out_string = fmt::format(
        "({},"   //  1: name
        "{},"    //  2: Virtual Memory size
        "{},"    //  3: Working Set Size
        "0,"     //  4: Nothing
        "{},"    //  5: Process Id
        "{},"    //  6: PageFile
        "{},"    //  7: User Time
        "{},"    //  8: Kernel Time
        "{},"    //  9: Handle Count
        "{},"    // 10: Thread COunt
        "{})\t"  // 11: Uptime
        "{}\n",  // 12: name

        user,                     //  1: name
        virtual_size / 1024,      //  2: Virtual Memory size
        working_set_size / 1024,  //  3: Working Set Size
                                  //  4: Nothing
        process_id,               //  5: Process Id
        pagefile_usage / 1024,    //  6: PageFile
        usermode_time,            //  7: User Time
        kernelmode_time,          //  8: Kernel Time
        process_handle_count,     //  9: Handle Count
        thread_count,             // 10: Thread COunt
        uptime,                   // 11: Uptime
        exe_file);                // name

    return out_string;
}

// returns FORMATTED table of the processes
std::wstring GetProcessListFromWmi(std::wstring_view separator) {
    wtools::WmiWrapper wmi;

    if (!wmi.open() || !wmi.connect(cma::provider::kWmiPathStd)) {
        XLOG::l(XLOG_FUNC + "cant access WMI");
        return {};
    }
    wmi.impersonate();

    // status will be ignored, ps doesn't support correct error processing
    // like other wmi sections
    auto [table, ignored] = wmi.queryTable({}, L"Win32_Process", separator,
                                           cfg::groups::global.getWmiTimeout());
    return table;
}

// code from legacy client:
std::string ExtractProcessOwner(HANDLE process) {
    // Get process token
    HANDLE raw_handle{wtools::InvalidHandle()};

    if (::OpenProcessToken(process, TOKEN_READ, &raw_handle) == FALSE) {
        if (::GetLastError() != ERROR_ACCESS_DENIED) {
            XLOG::t.w("Failed to open process  to get a token {} ",
                      ::GetLastError());
        }
        return {};
    }
    ON_OUT_OF_SCOPE(::CloseHandle(raw_handle));

    // First get size needed, TokenUser indicates we want user information from
    // given token
    DWORD process_info{0};
    ::GetTokenInformation(raw_handle, TokenUser, nullptr, 0, &process_info);

    // Call should have failed due to zero-length buffer.
    if (::GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        return {};
    }

    // Allocate buffer for user information in the token.
    std::vector<unsigned char> user_token(process_info, 0);
    auto *user_token_data = reinterpret_cast<PTOKEN_USER>(user_token.data());
    // Now get user information in the allocated buffer
    if (::GetTokenInformation(raw_handle, TokenUser, user_token_data,
                              process_info, &process_info) == FALSE) {
        XLOG::l.w("Failed to get token information {}", GetLastError());
        return {};
    }

    // Some vars that we may need
    SID_NAME_USE snu_sid_name_use{SidTypeUser};
    WCHAR user_name[MAX_PATH] = {0};
    DWORD user_name_length = MAX_PATH;
    WCHAR domain_name[MAX_PATH] = {0};
    DWORD domain_name_length = MAX_PATH;

    // Retrieve user name and domain name based on user's SID.
    if (::LookupAccountSidW(nullptr, user_token_data->User.Sid, user_name,
                            &user_name_length, domain_name, &domain_name_length,
                            &snu_sid_name_use) == TRUE) {
        std::string out = "\\\\" + wtools::ToUtf8(domain_name) + "\\" +
                          wtools::ToUtf8(user_name);
        return out;
    }

    return {};
}

namespace {
std::wstring GetFullPath(IWbemClassObject *wbem_object) {
    std::wstring process_name;
    auto executable_path =
        wtools::WmiTryGetString(wbem_object, L"ExecutablePath");

    if (executable_path.has_value()) {
        process_name = *executable_path;
    } else {
        process_name = wtools::WmiStringFromObject(wbem_object, L"Caption");
    }

    auto cmd_line = wtools::WmiTryGetString(wbem_object, L"CommandLine");
    if (!cmd_line) {
        return process_name;
    }

    int argc = 0;
    auto *argv = ::CommandLineToArgvW(cmd_line->c_str(), &argc);
    if (argv == nullptr) {
        return process_name;
    }

    ON_OUT_OF_SCOPE(::LocalFree(argv));
    for (int i = 1; i < argc; ++i) {
        if (argv[i] != nullptr) {
            process_name += std::wstring(L"\t") + argv[i];
        }
    }
    return process_name;
}

std::wstring BuildProcessName(IWbemClassObject *wbem_object,
                              bool use_full_path) {
    return use_full_path ? GetFullPath(wbem_object)
                         : wtools::WmiStringFromObject(wbem_object, L"Caption");
}

}  // namespace

// we need string here(null terminated for C-functions)
// returns 0 on error
time_t ConvertWmiTimeToHumanTime(const std::string &creation_date) {
    // check input
    if (creation_date.size() <= 14) {
        XLOG::l.w("Bad creation date from WMI '{}'", creation_date);
        return 0;
    }

    // parse string
    auto year = creation_date.substr(0, 4);
    auto month = creation_date.substr(4, 2);
    auto day = creation_date.substr(6, 2);

    auto hour = creation_date.substr(8, 2);
    auto minutes = creation_date.substr(10, 2);
    auto seconds = creation_date.substr(12, 2);

    // fill default fields(time-day-saving!)
    time_t current_time = std::time(nullptr);
    auto creation_tm = *std::localtime(&current_time);

    // fill variable fields data
    creation_tm.tm_year = std::strtol(year.c_str(), nullptr, 10) - 1900;
    creation_tm.tm_mon = std::strtol(month.c_str(), nullptr, 10) - 1;
    creation_tm.tm_mday = std::strtol(day.c_str(), nullptr, 10);

    creation_tm.tm_hour = std::strtol(hour.c_str(), nullptr, 10);
    creation_tm.tm_min = std::strtol(minutes.c_str(), nullptr, 10);
    creation_tm.tm_sec = std::strtol(seconds.c_str(), nullptr, 10);
    creation_tm.tm_isdst = -1;  // we do not know DST, so we will ask system

    // calculate with possible correction of not-so-important fields
    return ::mktime(&creation_tm);
}

namespace {
time_t GetWmiObjectCreationTime(IWbemClassObject *wbem_object) {
    auto wmi_time_wide =
        wtools::WmiStringFromObject(wbem_object, L"CreationDate");

    // calculate creation time
    return ConvertWmiTimeToHumanTime(wtools::ToUtf8(wmi_time_wide));
}

/// returns uptime
// on error returns 0 (reasonable, but unusual)
unsigned long long CreationTimeToUptime(time_t creation_time,
                                        IWbemClassObject *wbem_object) {
    // lambda for logging
    auto obj_name = [wbem_object]() {
        auto process_name = BuildProcessName(wbem_object, true);
        return wtools::ToUtf8(process_name);
    };

    // check that time is not 0(not error)
    if (creation_time == 0) {
        XLOG::l.w("Can't determine creation time of the process '{}'",
                  obj_name());

        return std::time(nullptr);
    }

    auto current_time = std::time(nullptr);

    // check that time is ok
    if (creation_time > current_time) {
        XLOG::l.w(
            "Creation time of process'{}' is ahead of the current time on [{}] seconds",
            obj_name(), creation_time - current_time);

        return 0;
    }

    return static_cast<unsigned long long>(current_time - creation_time);
}
}  // namespace

unsigned long long CalculateUptime(IWbemClassObject *wbem_object) {
    if (nullptr == wbem_object) {
        XLOG::l.bp(XLOG_FUNC + " nullptr as parameter");
        return 0;
    }

    // calculate creation time
    auto creation_time = GetWmiObjectCreationTime(wbem_object);

    return CreationTimeToUptime(creation_time, wbem_object);
}

// idiotic functions required for idiotic method we are using in legacy software
int64_t GetUint32AsInt64(IWbemClassObject *wbem_object,
                         const std::wstring &name) {
    VARIANT value;
    auto hres = wbem_object->Get(name.c_str(), 0, &value, nullptr, nullptr);
    if (SUCCEEDED(hres)) {
        ON_OUT_OF_SCOPE(::VariantClear(&value));
        return static_cast<int64_t>(
            wtools::WmiGetUint32(value));  // read 32bit unsigned and convert
                                           // to 64 bit signed
    }

    XLOG::l.e("Fail to get '{}' {:#X}", wtools::ToUtf8(name),
              static_cast<unsigned int>(hres));
    return 0;
};

std::string GetProcessOwner(int64_t pid) {
    auto process_id = static_cast<DWORD>(pid);
    auto *process_handle = ::OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, process_id);
    if (process_handle == nullptr) {
        XLOG::t("Can't open process [{}] status is [{}]. Check access rights.",
                process_id, ::GetLastError());
        return "SYSTEM";
    }
    ON_OUT_OF_SCOPE(::CloseHandle(process_handle));

    auto owner = ExtractProcessOwner(process_handle);
    if (owner.empty()) {
        // disabled noisy log
        XLOG::t("Owner of [{}] is empty, assuming system", process_id);
        return "SYSTEM";
    }

    return owner;
}

uint64_t GetWstringAsUint64(IWbemClassObject *wmi_object,
                            const std::wstring &name) {
    auto str = wtools::WmiTryGetString(wmi_object, name);
    if (!str) {
        XLOG::l.e("Name {} is not found", wtools::ToUtf8(name));
        return 0;
    }

    return ::wcstoull(str->c_str(), nullptr, 0);
}

std::string ProducePsWmi(bool use_full_path) {
    namespace rs = std::ranges;
    // auto processes = GetProcessListFromWmi();
    wtools::WmiWrapper wmi;

    if (!wmi.open() || !wmi.connect(cma::provider::kWmiPathStd)) {
        XLOG::l("PS is failed to conect to WMI");
        return {};
    }

    wmi.impersonate();
    auto *processes = wmi.queryEnumerator({}, L"Win32_Process");
    if (processes == nullptr) {
        XLOG::l("Skipping scanning, enumerator can't be opened");
        return {};
    }
    ON_OUT_OF_SCOPE(processes->Release());

    std::string out;
    while (true) {
        IWbemClassObject *object{nullptr};
        wtools::WmiStatus status{wtools::WmiStatus::ok};
        std::tie(object, status) = wtools::WmiGetNextObject(
            processes, cfg::groups::global.getWmiTimeout());
        if (object == nullptr) {
            break;
        }

        ON_OUT_OF_SCOPE(object->Release());

        auto process_id = GetUint32AsInt64(object, L"ProcessId");

        auto process_owner = GetProcessOwner(process_id);

        auto process_name = BuildProcessName(object, use_full_path);

        // some process name includes trash output which includes carriage
        // return. Example: is pascom client crash handler.
        rs::replace(process_name, L'\n', L' ');
        rs::replace(process_name, L'\r', L' ');

        auto uptime = CalculateUptime(object);

        auto handle_count = GetUint32AsInt64(object, L"HandleCount");
        auto thread_count = GetUint32AsInt64(object, L"ThreadCount");
        auto pagefile_use = GetUint32AsInt64(object, L"PagefileUsage");

        // strings with numbers:
        auto virtual_size = GetWstringAsUint64(object, L"VirtualSize");
        auto working_set = GetWstringAsUint64(object, L"WorkingSetSize");
        auto user_time = GetWstringAsUint64(object, L"UserModeTime");
        auto kernel_time = GetWstringAsUint64(object, L"KernelModeTime");

        out += OutputProcessLine(virtual_size, working_set, pagefile_use,
                                 uptime, user_time, kernel_time, process_id,
                                 handle_count, thread_count, process_owner,
                                 wtools::ToUtf8(process_name));
    }
    return out;
}

void Ps::loadConfig() {
    use_wmi_ = cfg::GetVal(cfg::groups::kPs, cfg::vars::kPsUseWmi, true);
    full_path_ = cfg::GetVal(cfg::groups::kPs, cfg::vars::kPsFullPath, false);
}

std::string Ps::makeBody() {
    if (!use_wmi_) {
        XLOG::l.e("Native PS NOT IMPLEMENTED!");
    }

    return ProducePsWmi(full_path_);
}

};  // namespace cma::provider
