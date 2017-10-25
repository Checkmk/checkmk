#include "MockWbem.h"
#include "MockWinApi.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "wmiHelper.h"

using namespace ::testing;

class wa_wmiHelperTest : public Test {
protected:
    StrictMock<MockWinApi> _mockwinapi;
    StrictMock<MockIEnumWbemClassObject> _mockenumerator;
};

TEST_F(wa_wmiHelperTest, Result_next_enumerator_null) {
    wmi::Result testResult(nullptr, _mockwinapi);
    ASSERT_FALSE(testResult.next());
}

TEST_F(wa_wmiHelperTest, Result_next_failure) {
    StrictMock<MockIWbemClassObject> testObject;
    EXPECT_CALL(_mockenumerator, Next(2500, 1, _, _))
        .WillOnce(DoAll(SetArgPointee<2>(&testObject), SetArgPointee<3>(1), Return(WBEM_NO_ERROR)))
        .WillOnce(Return(WBEM_E_FAILED));
    EXPECT_CALL(testObject, Release());
    EXPECT_CALL(_mockenumerator, Release());
    wmi::Result testResult(&_mockenumerator, _mockwinapi);
    ASSERT_FALSE(testResult.next());
}

TEST_F(wa_wmiHelperTest, Result_next_no_more_values) {
    StrictMock<MockIWbemClassObject> testObject;
    EXPECT_CALL(_mockenumerator, Next(2500, 1, _, _))
        .WillOnce(DoAll(SetArgPointee<2>(&testObject), SetArgPointee<3>(1), Return(WBEM_NO_ERROR)))
        .WillOnce(DoAll(SetArgPointee<3>(0), Return(WBEM_S_FALSE)));
    EXPECT_CALL(testObject, Release());
    EXPECT_CALL(_mockenumerator, Release());
    wmi::Result testResult(&_mockenumerator, _mockwinapi);
    ASSERT_FALSE(testResult.next());
}

TEST_F(wa_wmiHelperTest, Result_next_object_returned) {
    StrictMock<MockIWbemClassObject> testObject;
    EXPECT_CALL(_mockenumerator, Next(2500, 1, _, _))
        .Times(2)
        .WillRepeatedly(DoAll(SetArgPointee<2>(&testObject), SetArgPointee<3>(1), Return(WBEM_NO_ERROR)));
    EXPECT_CALL(testObject, Release()).Times(2);
    EXPECT_CALL(_mockenumerator, Release());
    wmi::Result testResult(&_mockenumerator, _mockwinapi);
    ASSERT_TRUE(testResult.next());
}

TEST_F(wa_wmiHelperTest, Result_next_wmi_timeout) {
    StrictMock<MockIWbemClassObject> testObject;
    EXPECT_CALL(_mockenumerator, Next(2500, 1, _, _))
        .WillOnce(DoAll(SetArgPointee<2>(&testObject), SetArgPointee<3>(1), Return(WBEM_NO_ERROR)))
        .WillOnce(DoAll(SetArgPointee<3>(0), Return(WBEM_S_TIMEDOUT)));
    EXPECT_CALL(testObject, Release());
    EXPECT_CALL(_mockenumerator, Release());
    wmi::Result testResult(&_mockenumerator, _mockwinapi);
    ASSERT_THROW(testResult.next(), wmi::Timeout);
}
