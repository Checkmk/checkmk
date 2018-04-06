#include "MockEnvironment.h"

MockEnvironment::MockEnvironment(Logger *logger, const WinApiInterface &winapi)
    : ::Environment(false, false, logger, winapi) {}

MockEnvironment::~MockEnvironment() {}
