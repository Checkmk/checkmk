#include "MockEnvironment.h"

MockEnvironment::MockEnvironment(Logger *logger, const WinApiAdaptor &winapi)
    : ::Environment(false, false, logger, winapi) {}

MockEnvironment::~MockEnvironment() {}
