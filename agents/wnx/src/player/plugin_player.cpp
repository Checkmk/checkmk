// plugin_player.cpp : This file contains the 'main' function. Program execution
// begins and ends there.
//

// Precompiled
#include "pch.h"

// system C
// system C++

// Project
#include "carrier.h"
#include "common/cmdline_info.h"
#include "common/mailslot_transport.h"
#include "on_start.h"
#include "player.h"
#include "player_api.h"

// print short info about usage plus potential comment about error
static void PlayerUsage(const std::wstring& Comment) {
    using namespace cma::exe::cmdline;
    if (Comment != L"") {
        printf("Error: %ls\n", Comment.c_str());
    }
    printf(
        "Usage:\n\t<this exe> %ls ...\n"
        "\t<this exe> %ls\n"
        "\t<this exe> <%ls|%ls> <name> <port> <id> <timeout> <\"exe\"|\"folder\"> ]\"exe\"|\"folder\"] ...\n"
        "\t name    - any string\n"
        "\t port    - output port in format xxxx:xxxxxxx\n"
        "\t id      - answer id in format id:unique_string\n"
        "\t timeout - timeout in format timeout:seconds\n",
        kTestParam, kHelpParam, kRunParam, kRunOnceParam);
    printf(
        "Example:\n\tplugin_player.exe -run jail mail:\\\\.\\\\global\\mailslot\\system_0 id:01234 timeout:10 \"c:\\Program Files(x86)\\check_mk_plugins\\\"\n");
}

namespace cma::player {

constexpr const wchar_t* kUniqueTestId = L"0345246";

struct TestStorage {
public:
    std::vector<uint8_t> buffer_;
    bool delivered_;
    uint64_t answer_id_;
    std::string peer_name_;
};

static TestStorage S_Storage;

bool MailboxCallback(const cma::MailSlot* Slot, const void* Data, int Len,
                     void* Context) {
    using namespace std::chrono;
    auto storage = (TestStorage*)Context;
    if (!storage) {
        xlog::l("error in param\n");
        return false;
    }

    // your code is here
    xlog::l("Received \"%d\"\n", Len);

    auto fname = cma::cfg::GetCurrentLogFileName();

    auto dt = static_cast<const cma::carrier::CarrierDataHeader*>(Data);
    switch (dt->type()) {
        case cma::carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            xlog::l("log: %s", (const char*)dt->data()).filelog(fname.c_str());
            break;

        case cma::carrier::DataType::kSegment:
            // IMPORTANT ENTRY POINT
            // Receive data for Section
            {
                nanoseconds duration_since_epoch(dt->answerId());
                time_point<steady_clock> tp(duration_since_epoch);
                auto data_source = static_cast<const uint8_t*>(dt->data());
                auto data_end = data_source + dt->length();
                std::vector<uint8_t> vectorized_data(data_source, data_end);
                S_Storage.buffer_ = vectorized_data;
                S_Storage.answer_id_ = dt->answerId();
                S_Storage.peer_name_ = dt->providerId();
                S_Storage.delivered_ = true;
                break;
            }

        case cma::carrier::DataType::kYaml:
            break;
    }

    return true;
}

// returns not very light object, but used rarely
// ergo no problem for us
static std::vector<std::wstring> ConvertArgstoPathArray(int argc,
                                                        wchar_t const* argv[]) {
    using namespace std;
    using namespace std::filesystem;
    vector<wstring> v;
    if (argc == 0) {
        path p = G_TestPath;
        if (exists(p))
            v.push_back(p.wstring());
        else
            xlog::l("Cannot find default path %ls", p.wstring());

    } else {
        if (argc > 24) argc = 24;  // limit a bit
        for (int i = 0; i < argc; i++) {
            path p = argv[i];
            if (p.wstring() == L"#") {
                if (exists(G_TestPath)) v.push_back(G_TestPath.wstring());
                break;
            }
            if (exists(p))
                v.push_back(p.wstring());
            else
                xlog::l("Cannot find path %ls", p.wstring());
        }
    }

    return v;
}

// #TODO make this function common
//  test [parameters]
int MainTest(int argc, wchar_t const* argv[]) {
    cma::MailSlot mailbox("WinAgentPlayerTest", 0);
    using namespace cma::carrier;
    using namespace cma::exe;
    using namespace std;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    mailbox.ConstructThread(MailboxCallback, 20, &S_Storage);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());

    // prepare parameters
    wstring port_param(internal_port.begin(), internal_port.end());

    wstring id_param = cmdline::kId;
    id_param += cmdline::kSplitter;
    id_param += kUniqueTestId;

    wstring timeout_param = cmdline::kTimeout;
    timeout_param += cmdline::kSplitter;
    timeout_param += std::to_wstring(5);

    auto path_array = ConvertArgstoPathArray(argc, argv);

    const wchar_t* local_argv[32];
    local_argv[0] = L"jail";
    local_argv[1] = port_param.c_str();
    local_argv[2] = id_param.c_str();
    local_argv[3] = timeout_param.c_str();
    int local_argc = 4;
    for (auto& p : path_array) {
        local_argv[local_argc] = p.c_str();
        ++local_argc;
    }

    // execute
    auto ret = MainRunOnce(local_argc, local_argv);
    if (ret != 0) {
        xlog::l("Test Failed with code %d", ret).print();
        return ret;
    }

    // wait
    int count = 100;
    while (count--) {
        if (!S_Storage.delivered_) {
            ::Sleep(100);
            continue;
        }

        if (S_Storage.buffer_.size() == 0) {
            return 100;
        }
        // processing and checking
        xlog::l("SUCCESSFUL TEST, GRATZ!").print();
        return 0;
    }

    xlog::l("Test Failed - no Answer from the Engine").print();
    return 1;
}

//  run [parameters]
int MainRun(int argc, wchar_t const* argv[]) {
    if (argc < 2) {
        PlayerUsage(L"");
        return 1;
    }

    return 1;
}

static bool CheckEnvironment() {
    using namespace cma;
    auto value = tools::win::GetEnv(cfg::envs::kMkStateDirName);
    if (value.empty()) return false;

    try {
        if (!std::filesystem::exists(value)) return false;

        return true;
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " Variable {} looks as invalid {} and {}",
                cfg::envs::kMkStateDirName, value, e.what());
    }
    return false;
}

// #TODO make this function common
// workhorse of execution
int RunMe(const std::wstring& PeerName,  // assigned by caller
          const std::wstring& Port,      // format as in carrier.h mail:*
          const std::wstring& Id,        // answer id, should be set
          const std::wstring& Timeout,   // how long wait for execution
          std::vector<std::wstring> Exe  // files and folders
) {
    using namespace std;
    using namespace std::chrono;
    using namespace cma::carrier;

    auto environment_valid = CheckEnvironment();
    if (!environment_valid) {
        std::string log_text =
            "Environment is not prepared during start the plugin player ";
        CoreCarrier::FireLogX(PeerName, Port, log_text);
        xlog::l("<%s>", log_text.c_str());
    }

    // create box for execution
    player::TheBox box;

    // start box with executable
    auto x = box.start(Id, Exe);

    // wait for end, this is SYNCHRONOUS operation
    auto timeout = cma::tools::ConvertToUint64(Timeout);
    seconds tout(timeout.has_value() ? timeout.value() : 0);
    auto hit_timeout = box.waitForAllProcesses(tout, true);
    if (hit_timeout) {
        // CoreCarrier::FireSend(PeerName, Port, Id, accu.data(), accu.size());
    }

    // accumulate results in vector
    vector<char> accu;
    int count = 0;

    box.processResults([&](const std::wstring CmdLine, uint32_t Pid,
                           uint32_t Code, const std::vector<char>& Data) {
        auto data = wtools::ConditionallyConvertFromUTF16(Data);
        XLOG::d("Process [{}]\t Pid [{}]\t Code [{}]\n---\n{}\n---\n",
                wtools::ConvertToUTF8(CmdLine), Pid, Code, data.data());

        CoreCarrier::FireLogX(PeerName, Port,
                              "Process [{}]\t Pid [{}]\t Code [{}]",
                              wtools::ConvertToUTF8(CmdLine), Pid, Code);

        cma::tools::AddVector(accu, data);
        count++;
    });

    // sends results to carrier
    CoreCarrier::FireSend(PeerName, Port, Id, accu.data(), accu.size());

    return 0;
}

// #TODO make this function common
//  runonce [parameters]
// params
// PORT ID TIMEOUT path1 path2 path3 ...
int MainRunOnce(int argc, wchar_t const* argv[]) {
    using namespace std;
    using namespace cma;
    using namespace cma::exe;
    if (argc < 4) {
        PlayerUsage(L"");
        return 1;
    }
    auto [error_val, name, id_val, timeout_val] =
        cma::exe::cmdline::ParseExeCommandLine(argc, argv);
    if (error_val != 0) return error_val;

    // path1 ...
    vector<wstring> exe;
    for (int i = 4; i < argc; i++) {
        exe.emplace_back(argv[i]);
    }

    return RunMe(name, argv[1], id_val, timeout_val, exe);
}

// main
int MainFunction(int argc, wchar_t const* argv[]) {
    // parse command line
    if (argc < 2) {
        PlayerUsage(L"");
        return 1;
    }

    using namespace cma::exe::cmdline;
    auto command = std::wstring(argv[1]);

    // First parameter removed - correction:
    argc -= 2;
    argv += 2;

    cma::OnStart(cma::AppType::srv);
    ON_OUT_OF_SCOPE(cma::OnExit());

    // check and call:
    if (command == kTestParam) return cma::player::MainTest(argc, argv);

    if (command == kRunParam) return cma::player::MainRun(argc, argv);

    if (command == kRunOnceParam) return cma::player::MainRunOnce(argc, argv);

    return 11;
}

}  // namespace cma::player

namespace cma {
AppType AppDefaultType() { return AppType::exe; }
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const* Argv[]) {
    return cma::player::MainFunction(argc, Argv);
}
#endif
