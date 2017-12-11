#include <winsock2.h>
#include <wtypesbase.h>
#include <functional>
#include <memory>
#include "MockWinApi.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "types.h"

using namespace ::testing;

class wa_typesTest : public Test {
protected:
    StrictMock<MockWinApi> _mockwinapi;
};

class wa_WrappedHandleTest : public wa_typesTest {};

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_invalid_handle) {
    // Note: StrictMock tests that CloseHandle is not called.
    WrappedHandle<InvalidHandleTraits> testHandle(_mockwinapi);
    ASSERT_EQ(INVALID_HANDLE_VALUE, testHandle.get());
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_valid_handle) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WrappedHandle<InvalidHandleTraits> testHandle(rawHandle, _mockwinapi);
        ASSERT_EQ(rawHandle, testHandle.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_move_construct) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(std::move(testHandle1));
        ASSERT_EQ(INVALID_HANDLE_VALUE, testHandle1.get());
        ASSERT_EQ(rawHandle, testHandle2.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_move_assign) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
        {
            testHandle2 = std::move(testHandle1);
            ASSERT_EQ(INVALID_HANDLE_VALUE, testHandle1.get());
            ASSERT_EQ(rawHandle1, testHandle2.get());
        }
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_release) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    // StrictMock checks that CloseHandle() is not called after release()
    {
        WrappedHandle<InvalidHandleTraits> testHandle(rawHandle, _mockwinapi);
        ASSERT_EQ(rawHandle, testHandle.release());
        ASSERT_EQ(INVALID_HANDLE_VALUE, testHandle.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_reset) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle(rawHandle1, _mockwinapi);
        EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
        testHandle.reset(rawHandle2);
        ASSERT_EQ(rawHandle2, testHandle.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_swap) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        testHandle1.swap(testHandle2);
        ASSERT_EQ(rawHandle2, testHandle1.get());
        ASSERT_EQ(rawHandle1, testHandle2.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_bool_true) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    WrappedHandle<InvalidHandleTraits> testHandle(rawHandle, _mockwinapi);
    ASSERT_TRUE(testHandle);
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_bool_false) {
    WrappedHandle<InvalidHandleTraits> testHandle(_mockwinapi);
    ASSERT_FALSE(testHandle);
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_function_swap) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        swap(testHandle1, testHandle2);
        ASSERT_EQ(rawHandle2, testHandle1.get());
        ASSERT_EQ(rawHandle1, testHandle2.get());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_equal_true) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(2);  // sic!
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle, _mockwinapi);
        ASSERT_TRUE(testHandle1 == testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_equal_false) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_FALSE(testHandle1 == testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_not_equal_true) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_TRUE(testHandle1 != testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_not_equal_false) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(2);  // sic!
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle, _mockwinapi);
        ASSERT_FALSE(testHandle1 != testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_less_than_true) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_TRUE(testHandle1 < testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_less_than_false) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(2);  // sic!
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle, _mockwinapi);
        ASSERT_FALSE(testHandle1 < testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest,
       InvalidHandleTraits_operator_less_than_or_equal_true) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_TRUE(testHandle1 <= testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest,
       InvalidHandleTraits_operator_less_than_or_equal_false) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x2);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_FALSE(testHandle1 <= testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_greater_than_true) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x2);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_TRUE(testHandle1 > testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_operator_greater_than_false) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(2);  // sic!
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle, _mockwinapi);
        ASSERT_FALSE(testHandle1 > testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest,
       InvalidHandleTraits_operator_greater_than_or_equal_true) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x2);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_TRUE(testHandle1 >= testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest,
       InvalidHandleTraits_operator_greater_than_or_equal_false) {
    HANDLE rawHandle1 = reinterpret_cast<HANDLE>(0x1);
    HANDLE rawHandle2 = reinterpret_cast<HANDLE>(0x2);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle1));
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle2));
    {
        WrappedHandle<InvalidHandleTraits> testHandle1(rawHandle1, _mockwinapi);
        WrappedHandle<InvalidHandleTraits> testHandle2(rawHandle2, _mockwinapi);
        ASSERT_FALSE(testHandle1 >= testHandle2);
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_stream_operator) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0xab);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WrappedHandle<InvalidHandleTraits> testHandle(rawHandle, _mockwinapi);
        std::ostringstream oss;
        oss << testHandle;
        const std::string expectedOutput{"0xab"};
        ASSERT_EQ(expectedOutput, oss.str());
    }
}

TEST_F(wa_WrappedHandleTest, InvalidHandleTraits_vector) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    size_t count = 3;
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle)).Times(count);
    {
        std::vector<HANDLE> rawHandles(count, rawHandle);
        std::vector<WrappedHandle<InvalidHandleTraits>> wrappedHandles;
        wrappedHandles.reserve(count);
        std::transform(rawHandles.cbegin(), rawHandles.cend(),
                       std::back_inserter(wrappedHandles), [this](HANDLE h) {
                           return WrappedHandle<InvalidHandleTraits>(
                               h, _mockwinapi);
                       });
        ASSERT_TRUE(std::all_of(
            wrappedHandles.cbegin(), wrappedHandles.cend(),
            [rawHandle](const WrappedHandle<InvalidHandleTraits> &w) {
                return rawHandle == w.get();
            }));
    }
}

TEST_F(wa_WrappedHandleTest, NullHandleTraits_invalid_handle) {
    // Note: StrictMock tests that CloseHandle is not called.
    WrappedHandle<NullHandleTraits> testHandle(_mockwinapi);
    ASSERT_EQ(nullptr, testHandle.get());
}

TEST_F(wa_WrappedHandleTest, NullHandleTraits_valid_handle) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    {
        WrappedHandle<NullHandleTraits> testHandle(rawHandle, _mockwinapi);
        ASSERT_EQ(rawHandle, testHandle.get());
    }
}

class wa_MutexLockTest : public wa_typesTest {};

TEST_F(wa_MutexLockTest, lock_unlock) {
    HANDLE rawHandle = reinterpret_cast<HANDLE>(0x1);
    EXPECT_CALL(_mockwinapi, CloseHandle(rawHandle));
    EXPECT_CALL(_mockwinapi, ReleaseMutex(rawHandle));
    {
        EXPECT_CALL(_mockwinapi, CreateMutex(nullptr, 0, nullptr))
            .WillOnce(Return(rawHandle));
        EXPECT_CALL(_mockwinapi, WaitForSingleObject(rawHandle, INFINITE));
        Mutex testMutex(_mockwinapi);
        MutexLock testLock(testMutex);
    }
}
