#include <iostream>
#include <memory>

#include "livestatus/Logger.h"
#include "livestatus/POSIXUtils.h"

int main() {
    setThreadName("main");
    Logger *logger_cmk = Logger::getLogger("cmk");
    logger_cmk->setUseParentHandlers(false);
    std::cout << "Hello world, Logger works\n";
    return 0;
}
