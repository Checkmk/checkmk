
// perf counter provider
// provide few different sections all related to the windows counters:

// if
// phydisk
// processor
// 'name'

// clang-format off

// Reasonable testing parameters
// -test
// -run mail:\\.\\global\mailslot\system_0
// -runonce mail:\\.\\global\mailslot\system_0 id:01234 timeout:10 234:phydisk 238:processor

// clang-format on

#include "pch.h"

#include <iostream>

#include "provider_api.h"

#include "carrier.h"

#include "tools/_misc.h"
#include "tools/_xlog.h"

#include "common/cmdline_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"

#include "fmt/format.h"

#include "providers/p_perf_counters.h"
#include "providers/perf_counters_cl.h"

#include "section_header.h"
#include "logger.h"
#include "cfg.h"

namespace cma::provider {

// print short info about usage plus potential comment about error
void ProgramUsage(const std::wstring& Comment) {
    using namespace cma::exe::cmdline;
    if (Comment != L"") {
        printf("Error: %ls\n", Comment.c_str());
    }
    printf(
        "Usage:\n\t<this exe> %ls ...\n"
        "\t<this exe> %ls\n"
        "\t<this exe> <%ls|%ls> <name> <port> <id> <timeout> <counterId:counterName> ...\n"
        "\t name    - any string\n"
        "\t port    - output port in format xxxx:xxxxxxx\n"
        "\t id      - answer id in format id:unique_string\n"
        "\t timeout - timeout in format timeout:seconds\n",
        kTestParam, kHelpParam, kRunParam, kRunOnceParam);
    printf(
        "Example:\n\tperf_counter.exe -run  mail:\\\\.\\\\global\\mailslot\\system_0 id:01234 timeout:10 234:winperf_:phydisk 238:winperf_:processor\n");
}

constexpr const wchar_t* kUniqueTestId = L"0345246";

struct TestStorage {
public:
    std::vector<uint8_t> buffer_;
    bool delivered_;
    uint64_t answer_id_;
    std::string peer_name_;
};

static TestStorage S_Storage;

// testing callback
bool MailboxCallbackTest(const cma::MailSlot* Slot, const void* Data, int Len,
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
            XLOG::l(XLOG::kNoPrefix)(  // command to out to file
                "{} : {}", dt->providerId(), (const char*)dt->data());
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
static std::vector<std::wstring> ConvertArgstoCounterArray(
    int argc, wchar_t const* argv[]) {
    using namespace std;
    if (argc == 0) {
        xlog::l("looks a s you start without counters - no output expected");
        return {};
    }

    vector<wstring> v;
    if (argc > 24) argc = 24;  // limit a bit
    for (int i = 0; i < argc; i++) {
        if (std::wstring(argv[i]) == L"#") break;
        v.push_back(argv[i]);
    }
    return v;
}

//  test [parameters]
int MainTest(int argc, wchar_t const* argv[]) {
    cma::MailSlot mailbox("WinAgentPlayerTest", 0);
    using namespace cma::carrier;
    using namespace cma::exe;
    using namespace std;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    mailbox.ConstructThread(MailboxCallbackTest, 20, &S_Storage);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());

    // prepare parameters
    wstring port_param(internal_port.begin(), internal_port.end());

    wstring id_param = cmdline::kId;
    id_param += cmdline::kSplitter;
    id_param += kUniqueTestId;

    wstring timeout_param = cmdline::kTimeout;
    timeout_param += cmdline::kSplitter;
    timeout_param += std::to_wstring(5);

    auto path_array = ConvertArgstoCounterArray(argc, argv);

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
        ProgramUsage(L"");
        return 1;
    }

    return 1;
}

//  runonce [parameters]
// params
// PORT ID TIMEOUT path1 path2 path3 ...
int MainRunOnce(int argc, wchar_t const* argv[]) {
    using namespace std;

    auto [error_val, name, id_val, timeout_val] =
        cma::exe::cmdline::ParseExeCommandLine(argc, argv);
    if (error_val != 0) return error_val;

    // path1 ...
    vector<wstring_view> counters;
    for (int i = 4; i < argc; i++) {
        counters.push_back(argv[i]);
    }

    return RunPerf(name, argv[1], id_val, stoi(timeout_val), counters);
}

// main
int MainFunction(int argc, wchar_t const* argv[]) {
    // parse command line
    if (argc < 2) {
        ProgramUsage(L"");
        return 1;
    }
    return MainFunctionCore(argc, argv);
}

}  // namespace cma::provider

namespace cma {
AppType AppDefaultType() { return AppType::exe; }
}  // namespace cma

#if !defined(CMK_TEST)
// This is our main. PLEASE, do not add code here
int wmain(int argc, wchar_t const* Argv[]) {
    return cma::provider::MainFunction(argc, Argv);
}
#endif
