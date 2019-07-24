//
// test-tools.cpp :

#include "pch.h"

#include "cfg.h"
#include "cma_core.h"

namespace cma::tools {
TEST(CmaTools, All) {
    const wchar_t* t[] = {L"a.exe", L"b", L"c"};
    EXPECT_FALSE(CheckArgvForValue(0, t, 0, "a.exe"))
        << "argc == 0 always returns false";
    EXPECT_FALSE(CheckArgvForValue(0, nullptr, 0, "a"))
        << "argv == nullptr always returns false";
    EXPECT_FALSE(CheckArgvForValue(1, nullptr, 1, "b"))
        << "pos >= argc always retursn false";

    EXPECT_TRUE(CheckArgvForValue(2, t, 1, "b"));
    EXPECT_FALSE(CheckArgvForValue(2, t, 2, "c"));
};

}  // namespace cma::tools
