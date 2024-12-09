#include <gtest/gtest.h>

#include <iostream>
#include <string>

#include "livestatus/Logger.h"
#include "livestatus/POSIXUtils.h"
#include "re2/re2.h"
#include "re2/stringpiece.h"

namespace {
bool check_livestatus_available() {
    setThreadName("main");
    Logger::getLogger("cmk")->setUseParentHandlers(false);
    std::cout << "Hello world, Logger works\n";
    return true;
}
}  // namespace

TEST(LivestatusAccess, Linked) { ASSERT_TRUE(check_livestatus_available()); }

TEST(Re2, Linked) {
    const std::string data{"AXzBCXz"};
    const re2::StringPiece input(data);

    ASSERT_TRUE(re2::RE2::FullMatch(input, re2::RE2{".*Xz"}));
}
