#include "EventLogVista.h"
#include "MockWinApi.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

using namespace ::testing;

namespace {
size_t callCount = 0;
BOOL WINAPI FakeEvtClose(EVT_HANDLE) {
    callCount++;
    return 1;
}

struct FakeEvtFunctionMap : public EvtFunctionMap {
    explicit FakeEvtFunctionMap(const WinApiInterface &winapi)
        : EvtFunctionMap(winapi) {
        this->close = FakeEvtClose;
    }
};
}  // namespace

class wa_EventHandleVistaTest : public Test {
public:
    wa_EventHandleVistaTest() { callCount = 0; }

protected:
    NiceMock<MockWinApi> _mockwinapi;
};

TEST_F(wa_EventHandleVistaTest, single_handle) {
    EVT_HANDLE rawHandle = reinterpret_cast<EVT_HANDLE>(0x1);
    HMODULE testModule = reinterpret_cast<HMODULE>(0x2);
    EXPECT_CALL(_mockwinapi, LoadLibraryW(_)).WillOnce(Return(testModule));
    FakeEvtFunctionMap testMap(_mockwinapi);
    ASSERT_EQ(0, callCount);
    {
        EventHandleVista testHandle(rawHandle, testMap);
        ASSERT_EQ(rawHandle, testHandle.get());
    }
    ASSERT_EQ(1, callCount);
}

TEST_F(wa_EventHandleVistaTest, vector) {
    EVT_HANDLE rawHandle = reinterpret_cast<EVT_HANDLE>(0x1);
    HMODULE testModule = reinterpret_cast<HMODULE>(0x2);
    EXPECT_CALL(_mockwinapi, LoadLibraryW(_)).WillOnce(Return(testModule));
    size_t count = 3;
    FakeEvtFunctionMap testMap(_mockwinapi);
    ASSERT_EQ(0, callCount);
    {
        std::vector<EVT_HANDLE> rawHandles(count, rawHandle);
        std::vector<EventHandleVista> wrappedHandles;
        wrappedHandles.reserve(count);
        std::transform(
            rawHandles.cbegin(), rawHandles.cend(),
            std::back_inserter(wrappedHandles),
            [&testMap](EVT_HANDLE h) { return EventHandleVista(h, testMap); });
        ASSERT_TRUE(std::all_of(wrappedHandles.cbegin(), wrappedHandles.cend(),
                                [rawHandle](const EventHandleVista &m) {
                                    return rawHandle == m.get();
                                }));
    }
    ASSERT_EQ(count, callCount);
}

TEST_F(wa_EventHandleVistaTest, vector_move_assign) {
    EVT_HANDLE rawHandle = reinterpret_cast<EVT_HANDLE>(0x1);
    HMODULE testModule = reinterpret_cast<HMODULE>(0x2);
    EXPECT_CALL(_mockwinapi, LoadLibraryW(_)).WillOnce(Return(testModule));
    size_t count = 3;
    FakeEvtFunctionMap testMap(_mockwinapi);
    ASSERT_EQ(0, callCount);
    {
        std::vector<EVT_HANDLE> rawHandles(count, rawHandle);
        std::vector<EventHandleVista> wrappedHandles;
        wrappedHandles.reserve(count);
        std::transform(
            rawHandles.cbegin(), rawHandles.cend(),
            std::back_inserter(wrappedHandles),
            [&testMap](EVT_HANDLE h) { return EventHandleVista(h, testMap); });
        // Test that all handles are closed when vector is replaced.
        wrappedHandles = std::move(std::vector<EventHandleVista>());
        ASSERT_EQ(count, callCount);
    }
}

TEST_F(wa_EventHandleVistaTest, vector_clear) {
    EVT_HANDLE rawHandle = reinterpret_cast<EVT_HANDLE>(0x1);
    HMODULE testModule = reinterpret_cast<HMODULE>(0x2);
    EXPECT_CALL(_mockwinapi, LoadLibraryW(_)).WillOnce(Return(testModule));
    size_t count = 3;
    FakeEvtFunctionMap testMap(_mockwinapi);
    ASSERT_EQ(0, callCount);
    {
        std::vector<EVT_HANDLE> rawHandles(count, rawHandle);
        std::vector<EventHandleVista> wrappedHandles;
        wrappedHandles.reserve(count);
        std::transform(
            rawHandles.cbegin(), rawHandles.cend(),
            std::back_inserter(wrappedHandles),
            [&testMap](EVT_HANDLE h) { return EventHandleVista(h, testMap); });
        // Test that all handles are closed when vector is cleared.
        wrappedHandles.clear();
        ASSERT_EQ(count, callCount);
    }
}
