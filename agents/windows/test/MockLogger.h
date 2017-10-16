#ifndef MockLogger_h
#define MockLogger_h

#include "Logger.h"
#include "gmock/gmock.h"

class MockLogger : public Logger {
public:
    MockLogger();
    virtual ~MockLogger();
    MOCK_CONST_METHOD0(getName, std::string());
    MOCK_CONST_METHOD0(getParent, Logger*());
    MOCK_CONST_METHOD0(getLevel, LogLevel());
    MOCK_METHOD1(setLevel, void(LogLevel level));
    MOCK_CONST_METHOD0(getHandler, Handler*());
    void setHandler(std::unique_ptr<Handler> handler) override {
        Handler *_handler = handler.release();
        auto helper = std::unique_ptr<Handler>(_handler);
        setHandlerImpl(helper);
    }
    MOCK_METHOD1(setHandlerImpl, void(std::unique_ptr<Handler> &handler));
    MOCK_CONST_METHOD0(getUseParentHandlers, bool());
    MOCK_METHOD1(setUseParentHandlers, void(bool useParentHandlers));
    MOCK_CONST_METHOD1(emitContext, void(std::ostream &));
    MOCK_METHOD1(log, void(const LogRecord &record));
};
#endif  // MockLogger_h
