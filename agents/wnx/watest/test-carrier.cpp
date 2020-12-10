// carrier test
//

#include "pch.h"

#include "carrier.h"
#include "commander.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "logger.h"
#include "read_file.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::carrier {  // to become friendly for wtools classes
TEST(PlayerTest, Pipe) {
    auto p = new wtools::SimplePipe();
    EXPECT_TRUE(p->getRead() == 0);
    EXPECT_TRUE(p->getWrite() == 0);
    p->create();
    EXPECT_TRUE(p->getRead() != 0);
    EXPECT_TRUE(p->getWrite() != 0);

    auto p2 = new wtools::SimplePipe();
    EXPECT_TRUE(p2->getRead() == 0);
    EXPECT_TRUE(p2->getWrite() == 0);
    p2->create();
    EXPECT_TRUE(p2->getRead() != 0);
    EXPECT_TRUE(p2->getWrite() != 0);
    delete p;
    delete p2;
}

struct TestStorage {
public:
    std::vector<uint8_t> buffer_;
    bool delivered_;
    uint64_t answer_id_;
    std::string peer_name_;
};

static TestStorage S_Storage;

bool MailboxCallbackCarrier(const cma::MailSlot* Slot, const void* Data,
                            int Len, void* Context) {
    using namespace std::chrono;
    auto storage = (TestStorage*)Context;
    if (!storage) {
        xlog::l("error in param\n");
        return false;
    }

    // your code is here
    XLOG::l("Received \"{}\"", Len);

    auto fname = cma::cfg::GetCurrentLogFileName();

    auto dt = static_cast<const cma::carrier::CarrierDataHeader*>(Data);
    switch (dt->type()) {
        case cma::carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            xlog::l("log: %s", dt->string().c_str()).filelog(fname.c_str());
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

TEST(CarrierTest, EstablishShutdown) {
    cma::MailSlot mailbox("WinAgentTest", 0);
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    mailbox.ConstructThread(MailboxCallbackCarrier, 20, &S_Storage);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());

    cma::carrier::CoreCarrier cc;
    // "mail"
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    EXPECT_EQ(cc.carrier_name_, kCarrierMailslotName);
    EXPECT_EQ(cc.carrier_address_, mailbox.GetName());
    cc.shutdownCommunication();

    // "asio"
    internal_port = BuildPortName(kCarrierAsioName, "127.0.0.1");  // port here
    ret = cc.establishCommunication(internal_port);
    EXPECT_FALSE(ret);
    std::string_view s = "Output from the asio";
    ret = cc.sendData("a", 11, s.data(), s.length());
    EXPECT_FALSE(ret);

    // bad port
    internal_port = BuildPortName("<GTEST>", "127.0.0.1");  // port here
    ret = cc.establishCommunication(internal_port);
    EXPECT_FALSE(ret);

    // "null"
    internal_port = BuildPortName(kCarrierNullName, "???");  // port here
    ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    s = "Output from the null";
    ret = cc.sendData("a", 11, s.data(), s.length());
    EXPECT_TRUE(ret);
    cc.shutdownCommunication();

    // "dump"
    internal_port = BuildPortName(kCarrierDumpName, "???");  // port here
    ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    s = "Output from the dump";
    ret = cc.sendData("a", 11, s.data(), s.length());
    EXPECT_TRUE(ret);
    cc.shutdownCommunication();

    // "file"
    internal_port =
        BuildPortName(kCarrierFileName, "fileout.dat.tmp");  // port here
    std::error_code ec;
    ON_OUT_OF_SCOPE(std::filesystem::remove("fileout.dat.tmp", ec));
    ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    ret = cc.sendData("a", 11, "aaa", 3);
    EXPECT_TRUE(ret);
    cc.shutdownCommunication();
}  // namespace cma::carrier

TEST(CarrierTest, Mail) {
    cma::MailSlot mailbox("WinAgentTest", 0);
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    mailbox.ConstructThread(MailboxCallbackCarrier, 20, &S_Storage);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());

    auto summary_output = cma::tools::ReadFileInVector(
        (tst::G_TestPath / L"summary.output").wstring().c_str());
    EXPECT_TRUE(summary_output);
    auto size = summary_output->size();

    S_Storage.buffer_.resize(0);
    S_Storage.delivered_ = false;

    cma::carrier::CoreCarrier cc;
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    EXPECT_EQ(kCarrierMailslotName, cc.carrier_name_);
    EXPECT_EQ(mailbox.GetName(), cc.carrier_address_);
    cc.sendData("a", 11, summary_output->data(), summary_output->size());
    cc.shutdownCommunication();

    int count = 100;
    while (count--) {
        if (!S_Storage.delivered_) {
            ::Sleep(100);
            continue;
        }

        EXPECT_EQ(S_Storage.answer_id_, 11);
        EXPECT_EQ(S_Storage.peer_name_, "a");
        EXPECT_EQ(S_Storage.buffer_, summary_output);

        return;
    }

    EXPECT_TRUE(false);
}

static std::string last;

bool TestRunCommand(std::string_view peer, std::string_view cmd) {
    last = cmd;
    return true;
}

// check that inform port works ok
TEST(CarrierTest, InformByMailSLot) {
    using namespace std::chrono;

    auto name_used = "WinAgentTestLocal";
    cma::MailSlot mailbox_client(name_used, 0);
    cma::MailSlot mailbox_server(name_used, 0);
    using namespace cma::carrier;
    auto internal_port = BuildPortName(kCarrierMailslotName,
                                       mailbox_server.GetName());  // port here
    cma::srv::ServiceProcessor processor;
    mailbox_server.ConstructThread(cma::srv::SystemMailboxCallback, 20,
                                   &processor);
    ON_OUT_OF_SCOPE(mailbox_server.DismantleThread());
    cma::tools::sleep(100ms);

    {
        cma::carrier::CoreCarrier cc;
        // "mail"
        auto ret = cc.establishCommunication(internal_port);
        ASSERT_TRUE(ret);
        ON_OUT_OF_SCOPE(cc.shutdownCommunication());

        cma::tools::sleep(100ms);

        auto save_rcp = cma::commander::ObtainRunCommandProcessor();
        ON_OUT_OF_SCOPE(cma::commander::ChangeRunCommandProcessor(save_rcp));
        cma::commander::ChangeRunCommandProcessor(TestRunCommand);

        InformByMailSlot(mailbox_client.GetName(), "xxx");
        cma::tools::sleep(100ms);
        EXPECT_EQ(last, "xxx");

        InformByMailSlot(mailbox_client.GetName(), "zzz");
        cma::tools::sleep(100ms);
        EXPECT_EQ(last, "zzz");
    }

}  // namespace cma::carrier

}  // namespace cma::carrier
