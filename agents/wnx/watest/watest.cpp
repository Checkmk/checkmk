// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.

//
#include "pch.h"

#include <processthreadsapi.h>  // for GetCurrentProcess, SetPriorityClass
#include <winbase.h>            // for HIGH_PRIORITY_CLASS

#include "carrier.h"  // for CarrierDataHeader, CoreCarrier, DataType, DataType::kLog, carrier
#include "common/mailslot_transport.h"  // for MailSlot
#include "common/wtools.h"  // for SecurityLevel, SecurityLevel::admin, SecurityLevel::standard
#include "gtest/gtest.h"  // for InitGoogleTest, RUN_ALL_TESTS
#include "logger.h"       // for ColoredOutputOnStdio
#include "on_start.h"     // for OnStart, AppType, AppType::test

using namespace std::chrono_literals;
namespace carrier = cma::carrier;

namespace cma {
AppType AppDefaultType() { return AppType::test; }

}  // namespace cma

namespace {
struct WatestMailSlot {
    ~WatestMailSlot() {
        if (established_) {
            cc_.shutdownCommunication();
        }

        if (maked_) {
            mailbox_.DismantleThread();
        }
    }
    bool makeSlot(wtools::SecurityLevel sl, bool &thread_exit) {
        if (maked_) {
            return true;
        }
        maked_ = mailbox_.ConstructThread(&WatestMailSlot::ThreadCallback, 20,
                                          &thread_exit, sl);
        return maked_;
    }

    bool connect() {
        if (established_) {
            return true;
        }
        established_ = cc_.establishCommunication(port());
        return established_;
    }
    bool sendLog(std::string_view text) {
        return cc_.sendLog("watest", static_cast<const void *>(text.data()),
                           text.length());
    }

protected:
    std::string port() const {
        return carrier::BuildPortName(carrier::kCarrierMailslotName,
                                      mailbox_.GetName());
    }
    static bool ThreadCallback(const cma::MailSlot *slot, const void *data,
                               int length, void *context) {
        auto dt = static_cast<const carrier::CarrierDataHeader *>(data);
        switch (dt->type()) {
            case carrier::DataType::kLog: {
                if (dt->data() == nullptr) {
                    XLOG::l(XLOG::kNoPrefix)("{} : null", dt->providerId());
                    break;
                }

                auto data = static_cast<const char *>(dt->data());
                std::string to_log;
                to_log.assign(data, data + dt->length());
                XLOG::l(XLOG::kNoPrefix)("{} : {}", dt->providerId(), to_log);

                if (to_log == "exit") {
                    *static_cast<bool *>(context) = true;
                }
                break;
            }

            default:
                break;
        }

        return true;
    }

private:
    cma::MailSlot mailbox_{"WatestMailSlot", 0};
    carrier::CoreCarrier cc_;
    bool established_{false};
    bool maked_{false};
};

void RunMailSlot(wtools::SecurityLevel sl) {
    WatestMailSlot wams;

    bool thread_exit{false};
    if (!wams.makeSlot(sl, thread_exit)) {
        XLOG::SendStringToStdio("Cant make", XLOG::Colors::red);
        return;
    }
    while (!thread_exit) {
        cma::tools::sleep(100ms);
    }
}

void SendToMailSlot() {
    WatestMailSlot wams;
    if (!wams.connect()) {
        XLOG::SendStringToStdio("Cant connect", XLOG::Colors::red);
        return;
    }
    wams.sendLog("Aaaaaaaaaaaaaaaaaaaaaaa\n");
    cma::tools::sleep(1s);
    wams.sendLog("exit");
}

}  // namespace

int wmain(int argc, wchar_t **argv) {
    using namespace std::literals;
    if (argc == 2 && argv[1] == L"wait"s) {
        cma::tools::sleep(1h);
        return 1;
    }

    std::set_terminate([]() {
        //
        XLOG::details::LogWindowsEventCritical(999, "Win Agent is Terminated.");
        XLOG::stdio.crit("Win Agent is Terminated.");
        XLOG::l.bp("WaTest is Terminated.");
        abort();
    });

    XLOG::setup::ColoredOutputOnStdio(true);

    if (argc >= 2 && std::wstring(argv[1]) == L"run_admin_mailslot") {
        RunMailSlot(wtools::SecurityLevel::admin);
        return 0;
    }

    if (argc >= 2 && std::wstring(argv[1]) == L"run_standard_mailslot") {
        RunMailSlot(wtools::SecurityLevel::standard);
        return 0;
    }

    if (argc >= 2 && std::wstring(argv[1]) == L"test_mailslot") {
        SendToMailSlot();
        return 0;
    }

    ::SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
    if (!cma::OnStart(cma::AppType::test)) {
        std::cout << "Fail Create Folders\n";
        return 33;
    }
    OnStart(cma::AppType::test);
    ::testing::InitGoogleTest(&argc, argv);
#if defined(_DEBUG)
    //::testing::GTEST_FLAG(filter) = "EventLogTest*";
    //::testing::GTEST_FLAG(filter) = "LogWatchEventTest*";  // CURRENT
    //::testing::GTEST_FLAG(filter) = "WinPerfTest*";
    //::testing::GTEST_FLAG(filter) = "AgentConfig*";
    //::testing::GTEST_FLAG(filter) = "PluginTest*";
    //::testing::GTEST_FLAG(filter) = "ExternalPortTest*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderMrpe*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderOhm*";
    // ::testing::GTEST_FLAG(filter) = "SectionProviderSpool*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderSkype*";
    //::testing::GTEST_FLAG(filter) = "CvtTest*";
    //::testing::GTEST_FLAG(filter) = "ProviderTest*";
    //::testing::GTEST_FLAG(filter) = "ProviderTest.WmiAll*";
    //::testing::GTEST_FLAG(filter) = "SectionProviderSkype*";
    //::testing::GTEST_FLAG(filter) = "Wtools*";
    //::testing::GTEST_FLAG(filter) = "CapTest*";
    // ::testing::GTEST_FLAG(filter) = "UpgradeTest*";
    // ::testing::GTEST_FLAG(filter) = "*Mrpe*";
    //::testing::GTEST_FLAG(filter) = "*OnlyFrom*";
    //::testing::GTEST_FLAG(filter) = "EncryptionT*";
#endif
    auto r = RUN_ALL_TESTS();
    if (!r) XLOG::stdio("Win Agent is exited with {}.", r);
    return r;
}
