//
// check_mk_service.cpp : This file contains ONLY the 'main' function.
//
// Precompiled
#include "pch.h"
// system C
// system C++
#include <filesystem>
#include <iostream>
#include <string>

#include "yaml-cpp/yaml.h"

// Project
#include "common/cmdline_info.h"
#include "install_api.h"
#include "windows_service_api.h"

// Personal
#include "cfg.h"
#include "check_mk_service.h"
#include "logger.h"
#include "providers/perf_counters_cl.h"

std::filesystem::path G_ProjectPath = PROJECT_DIR_CMK_SERVICE;

// print short info about usage plus potential comment about error
static void ServiceUsage(const std::wstring &Comment) {
    using namespace cma::cmdline;
    using namespace xlog::internal;
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::DuplicateOnStdio(true);
    if (Comment != L"") {
        printf("Error: %ls\n", Comment.c_str());
    }
    xlog::sendStringToStdio("Normal Usage:\n", Colors::kGreen);
    printf(
        "\t%s.exe <%ls|%ls|%ls>\n"
        "\t%-10ls - install as a service\n"
        "\t%-10ls - remove service\n"
        "\t%-10ls - usage\n",
        kServiceExeName,  // service name from th project definitions
        // first Row
        kInstallParam, kRemoveParam, kHelpParam,
        // second row
        kInstallParam, kRemoveParam, kHelpParam);

    xlog::sendStringToStdio("Common Testing:\n", Colors::kCyan);
    printf(
        "\t%s.exe <%ls|%ls [self seconds]|<%ls|%ls> [%ls]>\n"
        "\t%-10ls - legacy test\n"
        "\t%-10ls - short test. If self added, then agent simulates connection from monitoring site with seconds period\n"
        "\t%-10ls|%-10ls - executes as app(adhoc mode)\n"
        "\t\t%-10ls - logging on stdio\n",
        kServiceExeName,  // service name from th project definitions
        // first Row
        kLegacyTestParam, kTestParam, kExecParam, kAdhocParam, kExecParamExtend,
        // second row
        kLegacyTestParam, kTestParam, kExecParam, kAdhocParam,
        kExecParamExtend);

    xlog::sendStringToStdio("Realtime Testing:\n", Colors::kCyan);
    printf(
        "\t%s.exe <%ls>\n"
        "\t%-10ls - test realtime data with all sections and encryption\n",
        kServiceExeName,  // service name from th project definitions
        // first Row
        kRealtimeParam,
        // second row
        kRealtimeParam);

    xlog::sendStringToStdio(
        "To Convert Legacy Agent Ini File into Agent Yml file:\n",
        Colors::kPink);
    printf(
        "\t%s.exe %ls <inifile> [yamlfile]\n"
        "\tinifile - from Legacy Agent\n"
        "\tyamlfile - name of an output file(optional)\n",
        kServiceExeName,  // service name from th project definitions
                          // first Row
        kCvtParam);

    xlog::sendStringToStdio("To Activate/Deactivate Legacy Agent:\n",
                            Colors::kPink);
    printf(
        "\t%s.exe <%ls|%ls>\n"
        "\t%-10ls - stop and deactivate legacy agent\n"
        "\t%-10ls - activate and start legacy agent(only for testing)\n",
        kServiceExeName,  // service name from th project definitions

        // first Row
        kStopLegacyParam, kStartLegacyParam,
        // second row
        kStopLegacyParam, kStartLegacyParam);

    xlog::sendStringToStdio("To Upgrade Legacy Agent(migration):\n",
                            Colors::kPink);
    printf(
        "\t%s.exe %ls [force]\n"
        "\tforce - upgrading(migration) is forced\n",
        kServiceExeName,  // service name from th project definitions

        // first Row
        kUpgradeParam);

    xlog::sendStringToStdio(
        "To Install Bakery Files, plugins.cap and check_mk.ini, in install folder:\n",
        Colors::kPink);
    printf("\t%s.exe %ls\n",
           kServiceExeName,  // service name from th project definitions

           // first Row
           kCapParam);

    xlog::sendStringToStdio("To test Sections individually:\n", Colors::kCyan);
    printf(
        "\t%s.exe %ls <name> [number [trace]] \n"
        "\t\tname - allowed only df\n"
        "\t\tnumber - not 0: pause between tests in seconds, count of tests are infinite. 0 - test once\n"
        "\t\ttrace - log output on the stdio\n"
        "\t\t\t example '%s -section df 5 trace'\n"
        "\t\t\t test section df infinitely long with pause 5 seconds and log output on stdio\n",
        kServiceExeName,  // service name from th project definitions

        // first Row
        kSectionParam,
        // example row
        kServiceExeName);

    // undocummneted
    // -winnperf ....... command line for runperf
}

namespace cma {
namespace details {
extern bool G_Service;
}

AppType AppDefaultType() {
    return details::G_Service ? AppType::srv : AppType::exe;
}

template <typename T>
auto ToInt(const T W, int Dflt = 0) noexcept {
    try {
        return std::stoi(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToUInt64(const T W, uint64_t Dflt = 0) noexcept {
    try {
        return std::stoull(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToInt64(const T W, int64_t Dflt = 0) noexcept {
    try {
        return std::stoll(W);
    } catch (const std::exception &) {
        return Dflt;
    }
}

template <typename T>
auto ToUint(const T W, uint32_t Dflt = 0) noexcept {
    try {
        return static_cast<uint32_t>(std::stoul(W));
    } catch (const std::exception &) {
        return Dflt;
    }
}

// Command Lines
// -cvt watest/CheckMK/Agent/check_mk.test.ini
//

// #TODO Function is over complicated
// we want to test main function too.
// so we have main, but callable
int MainFunction(int argc, wchar_t const *Argv[]) {
    if (argc == 1) {
        // entry from the service engine

        using namespace cma::install;
        using namespace std::chrono;
        using namespace cma::cfg;

        cma::details::G_Service = true;  // we know that we are service

        return cma::srv::ServiceAsService(1000ms, [](const void *) {
            // optional commands listed here
            // ********
            // 1. Auto Update when  MSI file is located by specified address
            // this part of code have to be tested manually
            // scripting is possible but complicated
            CheckForUpdateFile(
                kDefaultMsiFileName,     // file we are looking for
                GetUpdateDir(),          // dir where file we're searching
                UpdateType::exec_quiet,  // quiet for production
                UpdateProcess::execute,  // start update when file found
                GetUserInstallDir());    // dir where file to backup
            return true;
        });
    }

    std::wstring param(Argv[1]);
    if (param == cma::exe::cmdline::kRunOnceParam) {
        // to test
        // -runonce winperf file:a.txt id:12345 timeout:20 238:processor
        // NO READING FROM CONFIG. This is intentional

        auto [error_val, name, id_val, timeout_val] =
            cma::exe::cmdline::ParseExeCommandLine(argc - 2, Argv + 2);

        if (error_val != 0) {
            XLOG::l("Invalid parameters in command line [{}]", error_val);
            return 1;
        }

        std::wstring prefix = name;
        std::wstring port = Argv[3];
        std::wstring id = id_val;
        std::wstring timeout = timeout_val;
        std::vector<std::wstring_view> counters;
        for (int i = 6; i < argc; i++) {
            if (std::wstring(L"#") == Argv[i]) break;
            counters.push_back(Argv[i]);
        }

        return cma::provider::RunPerf(prefix, id, port, ToInt(timeout, 20),
                                      counters);
    }

    if (0) {
        // this code is enabled only during testing and debugging
        auto path = G_ProjectPath;
        for (;;) {
            auto yml_test_file =
                G_ProjectPath / "data" / "check_mk.example.yml";
            try {
                YAML::Node config = YAML::LoadFile(yml_test_file.u8string());
            } catch (const std::exception &e) {
                XLOG::l(XLOG_FLINE + " exception %s", e.what());
            } catch (...) {
                XLOG::l(XLOG::kBp)(XLOG_FLINE + " exception bad");
            }
        }
    }

    using namespace cma::cmdline;
    cma::OnStartApp();  // path from EXE

    // #TODO, estimate mapping
    std::unordered_map<std::wstring, std::function<void()>> mapping = {
        {kInstallParam, []() {
             XLOG::l(XLOG::kStdio | XLOG::kInfo)("service to INSTALL");
             return srv::InstallMainService();
         }}};

    if (param == kInstallParam) {
        XLOG::l(XLOG::kStdio | XLOG::kInfo)("service to INSTALL");
        return cma::srv::InstallMainService();
    }
    if (param == kRemoveParam && argc > 2) {
        XLOG::l(XLOG::kStdio | XLOG::kInfo)("service to REMOVE");
        return cma::srv::RemoveMainService();
    }

    if (param == kTestParam) {
        std::wstring param = argc > 2 ? Argv[2] : L"";
        auto interval = argc > 3 ? ToInt(Argv[3]) : 0;
        return cma::srv::TestMainService(param, interval);
    }

    if (param == kLegacyTestParam) {
        return cma::srv::TestMainService(L"legacy", 0);
    }

    if (param == kExecParam) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        auto log_on_screen = second_param == kExecParamExtend
                                 ? cma::srv::StdioLog::yes
                                 : cma::srv::StdioLog::no;
        return cma::srv::ExecMainService(log_on_screen);
    }
    if (param == kRealtimeParam) {
        return cma::srv::ExecRealtimeTest(true);
    }
    if (param == kSkypeParam) {
        return cma::srv::ExecSkypeTest();
    }
    if (param == kStopLegacyParam) {
        return cma::srv::ExecStopLegacy();
    }
    if (param == kStartLegacyParam) {
        return cma::srv::ExecStartLegacy();
    }
    if (param == kCapParam) {
        return cma::srv::ExecCap();
    }
    if (param == kUpgradeParam) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        return cma::srv::ExecUpgradeParam(second_param == L"force");
    }
    if (param == kCvtParam && argc > 2) {
        std::wstring ini = argc > 2 ? Argv[2] : L"";
        std::wstring yml = argc > 3 ? Argv[3] : L"";
        return cma::srv::ExecCvtIniYaml(ini, yml, true);
    }
    if (param == kSectionParam && argc > 2) {
        std::wstring section = Argv[2];
        int delay = argc > 3 ? ToInt(Argv[3]) : 0;
        bool diag = argc > 4 ? std::wstring(Argv[4]) == L"trace" : false;
        return cma::srv::ExecSection(section, delay, diag);
    }

    if (param == kHelpParam) {
        ServiceUsage(std::wstring(L""));
        return 0;
    }

    ServiceUsage(std::wstring(L"Provided Parameter \"") + param +
                 L"\" is not allowed");
    return 2;
}
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const *Argv[]) {
    return cma::MainFunction(argc, Argv);
}
#endif
