#include <memory>
#include "StringUtils.h"
#include "gtest/gtest.h"

TEST(OffsetStringMacroColumn, dummy) {
    EXPECT_EQ("foobar", mk::unsafe_tolower("fOObAr"));
    EXPECT_EQ("blah  ", mk::lstrip("   blah  "));
}
