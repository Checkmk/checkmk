
// provides basic api to start and stop service
#include "stdafx.h"

#include "windows_service_api.h"  // windows api abstracted

#include <shlobj_core.h>

#include <chrono>
#include <cstdint>   // wchar_t when compiler options set weird
#include <iostream>  // test commands

#include "cap.h"
#include "cfg.h"
#include "common/wtools.h"
#include "cvt.h"
#include "external_port.h"  // windows api abstracted
#include "install_api.h"    // install
#include "realtime.h"
#include "service_processor.h"  // cmk service implementation class
#include "tools/_kbd.h"
#include "tools/_process.h"
#include "upgrade.h"

// out of namespace
bool G_SkypeTesting = false;

namespace cma {

namespace srv {
static std::string_view kYouHaveToBeElevatedMessage =
    "You have to be elevated to use this function.\nPlease, run as Administrator\n";
// on -install
// Doesn't create artifacts in program. Changes registry.
int InstallMainService() {
    XLOG::setup::ColoredOutputOnStdio(true);
    xlog::sendStringToStdio("Service to be installed...\n",
                            xlog::internal::Colors::green);
    if (!cma::tools::win::IsElevated()) {
        xlog::sendStringToStdio(kYouHaveToBeElevatedMessage.data(),
                                xlog::internal::Colors::red);
        return 1;
    }

    auto result = wtools::InstallService(
        cma::srv::kServiceName,         // Name of service
        cma::srv::kServiceDisplayName,  // Name to display
        cma::srv::kServiceStartType,    // Service start type
        nullptr,  // cma::srv::kServiceDependencies,  // Dependencies
        nullptr,  // cma::srv::kServiceAccount,       // Service running account
        nullptr   // cma::srv::kServicePassword       // Password of the account
    );
    return result ? 0 : 1;
}

// on -remove
// Doesn't create artifacts in program. Changes registry.
int RemoveMainService() {
    XLOG::setup::ColoredOutputOnStdio(true);
    xlog::sendStringToStdio("Service to be removed...\n",
                            xlog::internal::Colors::green);
    if (!cma::tools::win::IsElevated()) {
        xlog::sendStringToStdio(kYouHaveToBeElevatedMessage.data(),
                                xlog::internal::Colors::red);
        return 1;
    }

    auto result = wtools::UninstallService(cma::srv::kServiceName);
    return result ? 0 : 1;
}

// #POC: to be deleted
static bool execMsi() {
    wchar_t* str = nullptr;
    if (SHGetKnownFolderPath(FOLDERID_System, KF_FLAG_DEFAULT, NULL, &str) !=
        S_OK)
        return false;
    std::wstring exe = str;
    exe += L"\\msiexec.exe";
    std::string command;
    command.assign(exe.begin(), exe.end());
    std::wstring options =
        L" /i \"C:\\z\\m\\check_mk\\agents\\wnx\\build\\install\\Release\\check_mk_service.msi\" "
        L"REINSTALL=ALL REINSTALLMODE=amus "
        L" /quiet";

    // start process
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcess(nullptr,                          // application name
                       (LPWSTR)(exe + options).c_str(),  // Command line options
                       NULL,   // Process handle not inheritable
                       NULL,   // Thread handle not inheritable
                       FALSE,  // Set handle inheritance to FALSE
                       0,      // No creation flags
                       NULL,   // Use parent's environment block
                       NULL,   // Use parent's starting directory
                       &si,    // Pointer to STARTUPINFO structure
                       &pi))   // Pointer to PROCESS_INFORMATION structure
    {
        return false;
    }

    return true;
}

// #POC This is part of poc, testing command which finds an update file and
// execute it
static void CheckForCommand(std::string& Command) {
    Command = "";
    std::error_code ec;
    auto dir = std::filesystem::current_path(ec);
    std::cout << dir.u8string() << ": tick\n";
    try {
        constexpr const char* kUpdateFileCommandDone = "update.command.done";
        std::string done_file_name = kUpdateFileCommandDone;
        std::ifstream done_file(done_file_name.c_str(), std::ios::binary);

        if (done_file.good()) {
            // first stage - deleting file
            done_file.close();
            auto ret = ::DeleteFileA(done_file_name.c_str());
            if (!ret) {
                xlog::l("Cannot Delete File %s with error %d",
                        done_file_name.c_str(), GetLastError());
                return;
            }
        }
        constexpr const char* kUpdateFileCommand = "update.command";
        std::string command_file_name = kUpdateFileCommand;
        std::ifstream command_file(command_file_name.c_str(), std::ios::binary);

        if (!command_file.good()) return;  // nothing todo

        // now is more interesting event
        xlog::l("File %s found, try to exec command", command_file_name.c_str())
            .print();

        command_file.seekg(0, std::ios::end);
        int length = static_cast<int>(command_file.tellg());
        command_file.seekg(0, std::ios::beg);
        if (length > MAX_PATH) {
            // sanity check - too long file will be ignored
            xlog::l("File %s is too big", command_file_name.c_str()).print();
            return;
        }

        // store command & rename file
        char buffer[MAX_PATH * 2];
        command_file.read(buffer, length);
        buffer[length] = 0;
        command_file.close();
        auto ret =
            ::MoveFileA(command_file_name.c_str(), done_file_name.c_str());
        if (ret) {
            Command = buffer;
            xlog::l("To exec %s", Command.c_str());
            execMsi();
            return;
        }

        xlog::l("Cannot Rename File from to %s %s with error %d",
                done_file_name.c_str(), GetLastError());
    } catch (...) {
    }
    return;
}

// on -test self
int TestMainServiceSelf(int Interval) {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    bool stop = false;

    if (Interval < 0) Interval = 0;
    // not a best method to call thread, but this is only for VISUAL testing
    std::thread kick_and_print([&stop, Interval]() {
        auto port = cma::cfg::groups::global.port();

        using namespace asio;

        io_context ios;
        std::string address = "127.0.0.1";

        ip::tcp::endpoint endpoint(ip::make_address(address), port);

        asio::ip::tcp::socket socket(ios);
        std::error_code ec;

        // give some time to start main thread
        // this is tesing routine ergo so primitive method is ok
        cma::tools::sleep(1000);

        while (!stop) {
            auto enc = cma::cfg::groups::global.globalEncrypt();
            auto password = enc ? cma::cfg::groups::global.password() : "";
            socket.connect(endpoint, ec);
            if (ec.value() != 0) {
                XLOG::l("Can't connect to {}:{}, waiting for 5 seconds",
                        address, port);

                // method below is not good, still we do not want
                // to over complicate the code just for testing purposes
                for (int i = 0; i < 5; i++) {
                    if (stop) break;
                    cma::tools::sleep(1000);
                }
                if (stop) break;
                continue;
            }
            error_code error;
            std::vector<char> v;
            for (;;) {
                char text[4096];
                auto count = socket.read_some(asio::buffer(text), error);
                if (error.value()) break;
                if (count) {
                    v.insert(v.end(), text, text + count);
                }
            }
            XLOG::l.i("Received {} bytes", v.size());
            if (enc && password[0]) {
                XLOG::l.i("Decrypting {} bytes", v.size());
                // attempt to decode
                cma::encrypt::Commander e(password);
                auto size = v.size();
                v.resize(size + 1024);
                auto [ret, sz] = e.decode(v.data(), size, true);
                XLOG::l.i("Decrypted {} bytes {}", ret, sz);
            }
            socket.close();

            // methods below is not a good still we do not want
            // to over complicate the code just for testing purposes
            for (int i = 0; i < Interval; i++) {
                if (stop) break;
                cma::tools::sleep(1000);
            }
            if (Interval == 0) break;
        }
        XLOG::l.i("Leaving testing thread");
        if (Interval == 0) XLOG::l.i("\n\nPress any key to end program\n\n");
    });

    ExecMainService(StdioLog::no);  // blocking call waiting for keypress
    stop = true;
    if (kick_and_print.joinable()) {
        XLOG::l.i("Waiting for testing thread");
        kick_and_print.join();
        XLOG::l.i("!");
    }

    return 0;
}

int TestIo() {
    using namespace std::chrono;

    // simple test for ExternalPort. will be disabled in production.
    try {
        XLOG::setup::DuplicateOnStdio(true);
        XLOG::setup::ColoredOutputOnStdio(true);
        cma::world::ExternalPort port(nullptr);
        port.startIo([](const std::string Ip) -> std::vector<uint8_t> {
            return std::vector<uint8_t>();
        });  //
        XLOG::l.i("testing 10 seconds");
        std::this_thread::sleep_until(steady_clock::now() + 10000ms);
        port.shutdownIo();  //

    } catch (const std::exception& e) {
        xlog::l("Exception is not allowed here %s", e.what());
    }
    return 0;
}

int TestMt() {
    using namespace std::chrono;

    // test for main thread. will be disabled in production
    // to find file, read and start update POC.
    try {
        // XLOG::setup::DuplicateOnStdio(true);
        XLOG::setup::ColoredOutputOnStdio(true);
        using namespace std::chrono;
        std::string command = "";
        cma::srv::ServiceProcessor sp(2000ms, [&command](const void* Sp) {
            CheckForCommand(command);
            if (command[0]) {
                cma::tools::RunDetachedCommand(command);
                command = "";
            }
            return true;
        });
        XLOG::SendStringToStdio("Testing...\n\n", XLOG::Colors::green);
        sp.startTestingMainThread();
        XLOG::SendStringToStdio("\nPress any key\n", XLOG::Colors::green);
        cma::tools::GetKeyPress();
        sp.stopTestingMainThread();

    } catch (const std::exception& e) {
        xlog::l("Exception is not allowed here %s", e.what());
    }
    return 0;
}

int TestLegacy() {
    using namespace std::chrono;

    try {
        // test for main thread. will be disabled in production
        // to find file, read and start update POC.
        using namespace std::chrono;
        std::string command = "";
        cma::srv::ServiceProcessor sp(
            2000ms, [&command](const void* Sp) { return true; });
        sp.startServiceAsLegacyTest();
        sp.stopService();
    } catch (const std::exception& e) {
        xlog::l("Exception is not allowed here %s", e.what());
    }
    return 0;
}

// on -cvt
// may be used as internal API function to convert ini to yaml
// GTESTED internally
int ExecCvtIniYaml(std::filesystem::path IniFile,
                   std::filesystem::path YamlFile, StdioLog stdio_log) {
    //
    auto flag = stdio_log == StdioLog::no ? 0 : XLOG::kStdio;
    if (stdio_log != StdioLog::no) {
        XLOG::setup::ColoredOutputOnStdio(true);
    }
    namespace fs = std::filesystem;
    fs::path file = IniFile;
    std::error_code ec;
    if (!fs::exists(file, ec)) {
        XLOG::l(flag)("File not found '{}'", IniFile.u8string());
        return 3;
    }
    cma::cfg::cvt::Parser parser_converter;
    parser_converter.prepare();
    if (!parser_converter.readIni(file, false)) {
        XLOG::l(flag)("Failed Load '{}'", fs::absolute(IniFile).u8string());
        return 2;
    }
    auto yaml = parser_converter.emitYaml();

    try {
        if (YamlFile.empty()) {
            std::cout << yaml;
        } else {
            auto file = YamlFile;
            std::ofstream ofs(file.u8string());
            ofs << yaml;
            ofs.close();
            XLOG::l.i(flag, "Successfully Converted {} -> {}",
                      fs::absolute(IniFile).u8string(),
                      fs::absolute(YamlFile).u8string());
        }
    } catch (const std::exception& e) {
        XLOG::l(flag) << "Exception: '" << e.what() << "' in ExecCvtIniYaml"
                      << std::endl;
        return 1;
    }

    return 0;
}

std::vector<std::wstring> SupportedSections{
    wtools::ConvertToUTF16(cma::section::kDfName)};

// on -section
// NOT GTESTED
int ExecSection(const std::wstring& SecName, int RepeatPause,
                StdioLog stdio_log) {
    //
    XLOG::setup::ColoredOutputOnStdio(true);
    if (stdio_log == StdioLog::yes)
        XLOG::setup::EnableTraceLog(false);
    else
        XLOG::setup::EnableTraceLog(true);

    if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(true);

    auto y = cma::cfg::GetLoadedConfig();
    std::vector<std::string> sections;
    sections.emplace_back(wtools::ConvertToUTF8(SecName));
    cma::cfg::PutInternalArray(cma::cfg::groups::kGlobal,
                               cma::cfg::vars::kSectionsEnabled, sections);
    cma::cfg::ProcessKnownConfigGroups();
    cma::cfg::SetupEnvironmentFromGroups();

    while (1) {
        TestLegacy();
        if (RepeatPause <= 0) break;
        cma::tools::sleep(RepeatPause * 1000);
    }

    return 0;
}

// on -exec
// we run entry point as normal process
// this is testing routine probably eliminated from the production build
// THIS ROUTINE DOESN'T USE wtools::ServiceController and Windows Service API
// Just internal to debug logic
int ExecMainService(StdioLog stdio_log) {
    using namespace std::chrono;
    using namespace cma::install;
    XLOG::setup::ColoredOutputOnStdio(true);
    if (stdio_log == StdioLog::yes)
        XLOG::setup::EnableTraceLog(false);
    else
        XLOG::setup::EnableTraceLog(true);
    XLOG::SendStringToStdio(
        "Adhoc/Exec Mode,"
        "press any key to stop execution\n",
        XLOG::Colors::cyan);
    auto delay = 1000ms;
    auto processor =
        std::make_unique<ServiceProcessor>(delay, [](const void* Processor) {
    // default embedded callback for exec
    // At the moment does nothing
    // optional commands should be placed here
    // ********
#if 0
        // Auto Update when  MSI file is located by specified address
        CheckForUpdateFile(kDefaultMsiFileName, cma::cfg::GetUpdateDir(),
                           UpdateType::kMsiExecQuiet, true);
#endif
            return true;
        });

    processor->startService();

    try {
        // setup output
        if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(true);

        cma::tools::GetKeyPress();  // blocking  wait for key press
    } catch (const std::exception& e) {
        XLOG::l("Exception '{}'", e.what());
    }

    XLOG::l.i("Server is going to stop");
    processor->stopService();

    if (stdio_log != StdioLog::no) XLOG::setup::DuplicateOnStdio(false);

    return 0;
}

// on -cap
int ExecCap() {
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    XLOG::l.i("Installing...");
    cma::cfg::cap::Install();
    XLOG::l.i("End of!");
    return 0;
}

int ExecShowConfig(std::string_view sec) {
    XLOG::setup::ColoredOutputOnStdio(true);
    using namespace cma::cfg;
    const auto yaml = GetLoadedConfig();
    YAML::Node filtered_yaml =
        sec.empty() ? YAML::Clone(yaml) : YAML::Clone(yaml[sec.data()]);
    cma::cfg::RemoveInvalidNodes(filtered_yaml);
    YAML::Emitter emit;
    emit << filtered_yaml;
    XLOG::SendStringToStdio("# Environment Variables:\n", XLOG::Colors::green);
    ProcessPluginEnvironment([](std::string_view name, std::string_view value) {
        XLOG::stdio("# {}=\"{}\"\n", name, value);
    });

    auto files = wtools::ConvertToUTF8(cma::cfg::GetPathOfLoadedConfig());
    auto file_table = cma::tools::SplitString(files, ",");

    XLOG::SendStringToStdio("# Loaded Config Files:\n", XLOG::Colors::green);
    std::string markers[] = {"# system: ", "# bakery: ", "# user  : "};
    int i = 0;
    for (auto f : file_table) {
        XLOG::SendStringToStdio(markers[i++], XLOG::Colors::white);
        XLOG::SendStringToStdio(f + "\n");
    }

    XLOG::setup::ColoredOutputOnStdio(false);
    XLOG::stdio("\n# {}\n{}\n", sec, emit.c_str());

    return 0;
}

// on -start_legacy
int ExecStartLegacy() {
    using namespace cma::cfg::upgrade;

    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    FindActivateStartLegacyAgent();
    XLOG::l.i("End of!");

    return 0;
}

// on -stop_legacy
int ExecStopLegacy() {
    using namespace cma::cfg::upgrade;

    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    FindStopDeactivateLegacyAgent();
    XLOG::l.i("End of!");

    return 0;
}

// on -upgrade
int ExecUpgradeParam(bool Force) {
    using namespace cma::cfg::upgrade;

    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableTraceLog(true);
    UpgradeLegacy(Force ? Force::yes : Force::no);
    XLOG::l.i("End of!");

    return 0;
}

// simple scanner of multi_sz strings
// #TODO gtest?
const wchar_t* GetMultiSzEntry(wchar_t*& Pos, const wchar_t* End) {
    auto sz = Pos;
    if (sz >= End) return nullptr;

    auto len = wcslen(sz);
    if (len == 0) return nullptr;  // last string in multi_sz

    Pos += len + 1;
    return sz;
}

// on -skype
// verify that skype business is present
int ExecSkypeTest() {
    G_SkypeTesting = true;
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false););
    XLOG::l.i("<<<Skype testing>>>");
    cma::provider::SkypeProvider skype;
    auto result = skype.generateContent(cma::section::kUseEmbeddedName, true);
    XLOG::l.i("*******************************************************");
    if (result.size())
        XLOG::l.i("{}", result);
    else {
        auto counter_str = wtools::perf::ReadPerfCounterKeyFromRegistry(
            wtools::perf::PerfCounterReg::english);
        auto data = counter_str.data();
        const auto end = counter_str.data() + counter_str.size();
        for (;;) {
            // get id
            auto potential_id = GetMultiSzEntry(data, end);
            if (!potential_id) break;

            // get name
            auto potential_name = GetMultiSzEntry(data, end);
            if (!potential_name) break;

            // check name
            result += wtools::ConvertToUTF8(potential_id) + ": " +
                      wtools::ConvertToUTF8(potential_name) + "\n";
        }
        XLOG::l.i("{}", result);
    }
    XLOG::l.i("*******************************************************");
    XLOG::l.i("Using Usual Registry Keys:");

    auto skype_counters = cma::provider::internal::GetSkypeCountersVector();
    skype_counters->clear();
    skype_counters->push_back(L"Memory");
    skype_counters->push_back(L"510");
    result = skype.generateContent(cma::section::kUseEmbeddedName, true);

    XLOG::l.i("*******************************************************");
    XLOG::l.i("{}", result);
    XLOG::l.i("*******************************************************");
    //    skype.generateContent();
    XLOG::l.i("<<<Skype testing END>>>");
    return 0;
}

// on -skype
// verify that skype business is present
int ExecResetOhm() {
    G_SkypeTesting = true;
    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    XLOG::SendStringToStdio("Resetting OHM internally\n", XLOG::Colors::yellow);
    cma::srv::ServiceProcessor sp;
    sp.resetOhm();
    return 0;
}

constexpr static int kRtTestPort = 5555;
constexpr static std::string_view kRtTestPassword = "axecerc";

// Yet Another Test server for the checking output from realtime main thread
// do NOT use in production
class UdpServer {
public:
    UdpServer(asio::io_context& io_context, short port, bool Print)
        : socket_(io_context,
                  asio::ip::udp::endpoint(asio::ip::udp::v4(), port))
        , print_(Print) {
        do_receive();
    }

    void do_receive() {
        socket_.async_receive_from(
            asio::buffer(data_, max_length), sender_endpoint_,
            [this](std::error_code ec, std::size_t bytes_recvd) {
                do_processing(bytes_recvd);
                do_receive();  // asio trick to restart receive
            });
    }

private:
    void do_processing(size_t Length) {
        if (!print_ || Length == 0) return;

        // decoding
        auto [success, len] = crypt_.decode(
            data_ + cma::rt::kDataOffset, Length - cma::rt::kDataOffset, true);

        // printing
        if (success) {
            data_[cma::rt::kDataOffset + len] = 0;
            XLOG::l.t("{}",
                      std::string_view(data_ + cma::rt::kDataOffset, Length));
        } else {
            XLOG::l("Failed to decrypt data");
        }

        xlog::sendStringToStdio(
            "Press any key to STOP testing Realtime Sections\n",
            xlog::internal::Colors::pink);
    }

    const std::string password_{kRtTestPassword};
    cma::encrypt::Commander crypt_{password_};

    asio::ip::udp::socket socket_;
    asio::ip::udp::endpoint sender_endpoint_;
    enum { max_length = 16000 };
    char data_[max_length];
    bool print_ = false;
};

void RunTestingUdpServer(asio::io_context* IoContext, int Port, bool Print) {
    try {
        UdpServer s(*IoContext, Port, Print);

        IoContext->run();  // blocking call till the context stopped
    } catch (std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }
}

// on -rt
// verify that skype business is present
int ExecRealtimeTest(bool Print) {
    using namespace cma::rt;

    XLOG::setup::DuplicateOnStdio(true);
    XLOG::setup::ColoredOutputOnStdio(true);
    ON_OUT_OF_SCOPE(XLOG::setup::DuplicateOnStdio(false););
    Device dev;
    asio::io_context context;
    std::thread thread_with_server(RunTestingUdpServer, &context, kRtTestPort,
                                   Print);

    auto ret = dev.start();

    xlog::sendStringToStdio(
        "Press any key to START testing Realtime Sections\n",
        xlog::internal::Colors::green);
    cma::tools::GetKeyPress();  // blocking  wait for key press
    dev.connectFrom("127.0.0.1", kRtTestPort,
                    {"mem", "df", "winperf_processor"}, kRtTestPassword, 30);
    cma::tools::GetKeyPress();  // blocking  wait for key press
    dev.stop();

    context.stop();
    if (thread_with_server.joinable()) thread_with_server.join();
    return 0;
}

// entry point in service mode
// normally this is "BLOCKING FOR EVER"
// called by Windows Service Manager
// exception free
// returns -1 on failure
int ServiceAsService(
    std::chrono::milliseconds Delay,
    std::function<bool(const void* Processor)> InternalCallback) noexcept {
    XLOG::l.i("service to run");

    cma::OnStartApp();               // path from service
    ON_OUT_OF_SCOPE(cma::OnExit());  // we are sure that this is last foo

    SelfConfigure();

    // infinite loop to protect from exception
    while (1) {
        try {
            std::unique_ptr<wtools::BaseServiceProcessor> processor =
                std::make_unique<ServiceProcessor>(Delay, InternalCallback);

            wtools::ServiceController service_controller(std::move(processor));
            auto ret = service_controller.registerAndRun(
                cma::srv::kServiceName);  // we will stay here till
                                          // service will be stopped
                                          // itself or from outside
            switch (ret) {
                case wtools::ServiceController::StopType::normal:
                    XLOG::l.i("Service is stopped normally");
                    return 0;

                case wtools::ServiceController::StopType::fail:
                    XLOG::l.i("Service is stopped due to abnormal situation");
                    return -1;
                case wtools::ServiceController::StopType::no_connect:
                    // may happen when we try to call usual exe
                    return 0;
            }
        } catch (const std::exception& e) {
            XLOG::l.crit("Exception hit {} in ServiceAsService", e.what());
        } catch (...) {
            XLOG::l.crit("Unknown Exception in ServiceAsService");
        }
    }
    // reachable only on service stop
}

// we are setting service as restartable using more or less suitable parameters
// set
// returns false if failed call
bool ConfigureServiceAsRestartable(SC_HANDLE handle) {
    SERVICE_FAILURE_ACTIONS service_fail_actions;
    SC_ACTION fail_actions[3];

    fail_actions[0].Type =
        SC_ACTION_RESTART;         // Failure action: Restart Service
    fail_actions[0].Delay = 2000;  // in milliseconds = 2minutes
    fail_actions[1].Type = SC_ACTION_RESTART;
    fail_actions[1].Delay = 2000;
    fail_actions[2].Type = SC_ACTION_RESTART;
    fail_actions[2].Delay = 2000;

    service_fail_actions.dwResetPeriod =
        3600;  // Reset Failures Counter, in Seconds
    service_fail_actions.lpCommand = nullptr;  // on service failure, not used
    service_fail_actions.lpRebootMsg =
        nullptr;  // Message during rebooting computer
                  // due to service failure, not used

    service_fail_actions.cActions = 3;  // Number of failure action to manage
    service_fail_actions.lpsaActions = fail_actions;

    auto result =
        ::ChangeServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS,
                               &service_fail_actions);  // Apply above settings
    if (!result) {
        XLOG::l("Error [{}] configuring service", GetLastError());
        return false;
    }

    return true;
}

// returns allocated data on success
SERVICE_FAILURE_ACTIONS* GetServiceFailureActions(SC_HANDLE handle) {
    SERVICE_FAILURE_ACTIONS* actions = nullptr;

    DWORD bytes_needed = 0;
    DWORD new_buf_size = 0;
    if (!::QueryServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS, NULL, 0,
                               &bytes_needed)) {
        auto dwError = ::GetLastError();
        if (ERROR_INSUFFICIENT_BUFFER != dwError) return nullptr;

        // allocation
        new_buf_size = bytes_needed;
        actions = reinterpret_cast<SERVICE_FAILURE_ACTIONS*>(
            ::LocalAlloc(LMEM_FIXED, new_buf_size));
    }

    if (::QueryServiceConfig2(handle, SERVICE_CONFIG_FAILURE_ACTIONS,
                              reinterpret_cast<LPBYTE>(actions), new_buf_size,
                              &bytes_needed))
        return actions;

    // we have to kill our actions data here
    if (actions) LocalFree(actions);

    return nullptr;
}

// complementary function to GetServiceFailuerActions
void DeleteServiceFailureActions(SERVICE_FAILURE_ACTIONS* actions) {
    if (actions) ::LocalFree(actions);
}

// returns true ALSO on error(to avoid useless attempts to configure
// non-configurable)
bool IsServiceConfigured(SC_HANDLE handle) {
    auto actions = GetServiceFailureActions(handle);
    ON_OUT_OF_SCOPE(DeleteServiceFailureActions(actions));

    if (actions) return actions->cActions != 0;

    XLOG::l("QueryServiceConfig2 failed [{}]", ::GetLastError());
    return true;
}

// handle must be killed with CloseServiceHandle
SC_HANDLE SelfOpen() {
    auto manager_handle = ::OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (nullptr == manager_handle) {
        XLOG::l.crit("Cannot open SC Manager {}", ::GetLastError());
        return nullptr;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(manager_handle));

    auto handle = ::OpenService(manager_handle, cma::srv::kServiceName,
                                SERVICE_ALL_ACCESS);
    if (nullptr == handle) {
        XLOG::l.crit("Cannot open Service {}, error =  {}",
                     wtools::ConvertToUTF8(cma::srv::kServiceName),
                     ::GetLastError());
    }

    return handle;
}

void SelfConfigure() {
    auto handle = SelfOpen();
    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));
    if (!IsServiceConfigured(handle)) {
        XLOG::l.i("Configure check mk service");
        ConfigureServiceAsRestartable(handle);
    }
}

}  // namespace srv
}  // namespace cma
