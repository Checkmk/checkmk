#include <gtest/gtest.h>

#include <memory>
#include <string>

#include "livestatus/Logger.h"
#include "livestatus/POSIXUtils.h"
#include "re2/re2.h"
#include "re2/stringpiece.h"

namespace {
bool check_livestatus_available() {
    setThreadName("main");
    Logger::getLogger("cmk")->setUseParentHandlers(false);
    return true;
}
}  // namespace

TEST(LivestatusAccess, Linked) { ASSERT_TRUE(check_livestatus_available()); }

TEST(Re2, Linked) {
    const std::string data{"AXzBCXz"};
    const re2::StringPiece input(data);

    ASSERT_TRUE(re2::RE2::FullMatch(input, re2::RE2{".*Xz"}));
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    // The code under test logs quite a bit via the "test" logger, which would
    // only clutter the test output. We drop those messages, but keep the log
    // level, so the logging code paths are still exercised.
    Logger::getLogger("test")->setHandler(nullptr);
    return RUN_ALL_TESTS();
}
