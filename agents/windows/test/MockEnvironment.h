#ifndef MockEnvironment_h
#define MockEnvironment_h

#include "Environment.h"
#include "gmock/gmock.h"

class Logger;
class WinApiAdaptor;

class MockEnvironment : public ::Environment {
public:
    MockEnvironment(Logger *logger, const WinApiAdaptor &winapi);
    virtual ~MockEnvironment();

    MOCK_CONST_METHOD0(hostname, std::string());
    MOCK_CONST_METHOD0(currentDirectory, std::string());
    MOCK_CONST_METHOD0(agentDirectory, std::string());
    MOCK_CONST_METHOD0(pluginsDirectory, std::string());
    MOCK_CONST_METHOD0(configDirectory, std::string());
    MOCK_CONST_METHOD0(localDirectory, std::string());
    MOCK_CONST_METHOD0(spoolDirectory, std::string());
    MOCK_CONST_METHOD0(stateDirectory, std::string());
    MOCK_CONST_METHOD0(tempDirectory, std::string());
    MOCK_CONST_METHOD0(logDirectory, std::string());
    MOCK_CONST_METHOD0(binDirectory, std::string());
    MOCK_CONST_METHOD0(logwatchStatefile, std::string());
    MOCK_CONST_METHOD0(eventlogStatefile, std::string());
    MOCK_CONST_METHOD0(workersJobObject, const JobHandle<0>&());
    MOCK_CONST_METHOD0(withStderr, bool());
    MOCK_CONST_METHOD0(isWinNt, bool());
    MOCK_CONST_METHOD0(winVersion, uint16_t());
};

#endif  // MockEnvironment_h
