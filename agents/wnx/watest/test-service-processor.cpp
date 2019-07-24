// test-section_processor.cpp

//
#include "pch.h"

#include "cfg.h"
#include "common/wtools.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::srv {

TEST(AsyncAnswerTest, Base) {
    AsyncAnswer aa;
    EXPECT_EQ(aa.order_, AsyncAnswer::Order::plugins_last);
    aa.prepareAnswer("aaa");

    EXPECT_EQ(aa.external_ip_, "aaa");
    EXPECT_EQ(aa.awaiting_segments_, 0);
    EXPECT_EQ(aa.received_segments_, 0);
    EXPECT_TRUE(aa.data_.empty());
    EXPECT_TRUE(aa.segments_.empty());
    EXPECT_TRUE(aa.plugins_.empty());
    EXPECT_TRUE(aa.local_.empty());
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
    aa.external_ip_ = "";
    aa.awaiting_segments_ = 1;
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
    aa.external_ip_ = "";
    aa.awaiting_segments_ = 0;
    aa.received_segments_ = 1;
    EXPECT_FALSE(aa.prepareAnswer("aaa"));
}

TEST(ServiceControllerTest, StartStopExe) {
    using namespace cma::srv;
    using namespace cma::cfg;
    using namespace std::chrono;
    int counter = 0;
    auto processor =
        new ServiceProcessor(100ms, [&counter](const void* Processor) {
            xlog::l("pip").print();
            counter++;
            return true;
        });
    ON_OUT_OF_SCOPE(delete processor;);

    cma::MailSlot mailbox(kServiceMailSlot, 0);
    mailbox.ConstructThread(SystemMailboxCallback, 20, processor);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    using namespace cma::carrier;
    processor->internal_port_ =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());

    auto tp = processor->openAnswer("127.0.0.1");

    // make command line
    auto cmd_line = groups::winperf.buildCmdLine();
    ASSERT_TRUE(!cmd_line.empty());
    auto count = groups::winperf.countersCount();
    auto count_of_colon = std::count(cmd_line.begin(), cmd_line.end(), L':');
    auto count_of_spaces = std::count(cmd_line.begin(), cmd_line.end(), L' ');
    ASSERT_TRUE(count_of_colon == count);
    ASSERT_EQ(count_of_spaces, count - 1);

    auto exe_name = groups::winperf.exe();
    ASSERT_TRUE(!exe_name.empty());
    auto wide_exe_name = wtools::ConvertToUTF16(exe_name);
    auto prefix = groups::winperf.prefix();
    ASSERT_TRUE(!prefix.empty());
    auto wide_prefix = wtools::ConvertToUTF16(prefix);

    processor->kickExe(true, wide_exe_name, tp.value(), processor, wide_prefix,
                       10, cmd_line);

    auto result = processor->getAnswer(1);
    EXPECT_TRUE(!result.empty());
}
}  // namespace cma::srv
