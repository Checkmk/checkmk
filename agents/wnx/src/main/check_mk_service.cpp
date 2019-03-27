//
// check_mk_service.cpp : This file contains ONLY the 'main' function.
//
// Precompiled
#include <pch.h>
// system C
// system C++
#include <filesystem>
#include <iostream>
#include <string>

#include "yaml-cpp/yaml.h"

// Project
#include "common/cmdline_info.h"
#include "service_api.h"
#include "windows_service_api.h"

// Personal
#include "check_mk_service.h"

#include "cfg.h"
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
        "\t%s.exe <%ls|%ls [self seconds]|%ls>\n"
        "\t%-10ls - legacy test\n"
        "\t%-10ls - short test. If self added, then agent simulates connection from monitoring site with seconds period\n"
        "\t%-10ls - exec as app(adhoc)\n",
        kServiceExeName,  // service name from th project definitions
        // first Row
        kLegacyTestParam, kTestParam, kExecParam,
        // second row
        kLegacyTestParam, kTestParam, kExecParam);

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

    xlog::sendStringToStdio("To Upgrade Legacy Agent:\n", Colors::kPink);
    printf(
        "\t%s.exe %ls [force]\n"
        "\tforce - optional parameter to force upgrading\n",
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
bool G_Service = false;
StartTypes AppDefaultType() {
    return G_Service ? StartTypes::kService : StartTypes::kExe;
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
    // check for invalid parameters count
    using namespace std::chrono;
    using namespace cma::install;
    if (argc == 1) {
        XLOG::l.i("service to run");
        using namespace cma::srv;
        G_Service = true;
        cma::OnStartApp();  // path from service
        ON_OUT_OF_SCOPE(cma::OnExit());
        return ServiceAsService(1000ms, [](const void *) {
            // optional commands listed here
            // ********
            // 1. Auto Update when  msi file is located by specified address
            CheckForUpdateFile(kDefaultMsiFileName, GetMsiUpdateDirectory(),
                               UpdateType::kMsiExecQuiet, true);
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
    } else if (param == kRemoveParam && argc > 2) {
        XLOG::l(XLOG::kStdio | XLOG::kInfo)("service to REMOVE");
        return cma::srv::RemoveMainService();
    } else if (param == kTestParam) {
        std::wstring param = argc > 2 ? Argv[2] : L"";
        auto interval = argc > 3 ? ToInt(Argv[3]) : 0;
        return cma::srv::TestMainService(param, interval);
    } else if (param == kLegacyTestParam) {
        return cma::srv::TestMainService(L"legacy", 0);
    } else if (param == kExecParam) {
        return cma::srv::ExecMainService();
    } else if (param == kSkypeParam) {
        return cma::srv::ExecSkypeTest();
    } else if (param == kStopLegacyParam) {
        return cma::srv::ExecStopLegacy();
    } else if (param == kStartLegacyParam) {
        return cma::srv::ExecStartLegacy();
    } else if (param == kCapParam) {
        return cma::srv::ExecCap();
    } else if (param == kUpgradeParam) {
        std::wstring second_param = argc > 2 ? Argv[2] : L"";
        return cma::srv::ExecUpgradeParam(second_param == L"force");
    } else if (param == kCvtParam && argc > 2) {
        std::wstring ini = argc > 2 ? Argv[2] : L"";
        std::wstring yml = argc > 3 ? Argv[3] : L"";
        return cma::srv::ExecCvtIniYaml(ini, yml, true);
    } else if (param == kSectionParam && argc > 2) {
        std::wstring section = Argv[2];
        int delay = argc > 3 ? ToInt(Argv[3]) : 0;
        bool diag = argc > 4 ? std::wstring(Argv[4]) == L"trace" : false;
        return cma::srv::ExecSection(section, delay, diag);
    } else if (param == kHelpParam) {
        ServiceUsage(std::wstring(L""));
        return 0;
    } else {
        ServiceUsage(std::wstring(L"Provided Parameter \"") + param +
                     L"\" is not allowed");
        return 2;
    }

    return 0;
}
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const *Argv[]) {
    return cma::MainFunction(argc, Argv);
}
#endif
