#include <gtest/gtest.h>

#include <iostream>
#include <string>

#include "livestatus/Logger.h"
#include "livestatus/POSIXUtils.h"

bool check_livestatus_available() {
    setThreadName("main");
    Logger *logger_cmk = Logger::getLogger("cmk");
    logger_cmk->setUseParentHandlers(false);
    std::cout << "Hello world, Logger works\n";
    return true;
}

// Demonstrate some basic assertions.
TEST(LivestatusAccess, Linked) { ASSERT_TRUE(check_livestatus_available()); }