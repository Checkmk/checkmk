// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <chrono>
#include <filesystem>

#include "cfg_details.h"
#include "common/object_repo.h"
#pragma warning(disable : 4996)  // have to test deprectaed API too

namespace cma {

TEST(ObjectRepo, CheckShared) {
    MicroRepo<int> f;
    EXPECT_TRUE(f.count() == 0);
    MicroRepo<std::string> fs;
    auto s = fs.createObject("a", "a string");
    ASSERT_TRUE(s);
    EXPECT_EQ(*s, "a string");
    EXPECT_TRUE(fs.count() == 1);

    {
        MicroRepo<std::string> fs;
        const std::string val = "cxdddddddddddddddddddddddddddd";
        auto a1 = fs.createObject("b", val);
        EXPECT_TRUE(fs.count() == 1);
        auto a2 = fs.createObject("c", val);
        EXPECT_TRUE(fs.count() == 2);
        auto a3 = fs.createObject("d", val);
        EXPECT_TRUE(fs.count() == 3);
        auto a4 = fs.createObject("e", val);
        EXPECT_TRUE(fs.count() == 4);
        EXPECT_EQ(*a4, val);
        for (auto k = 0; k < 100000; k++) {
            auto a3 = fs.createObject("a", val);
            ;
        }
        EXPECT_TRUE(fs.count() == 5);

        for (const auto &v : {"a", "b", "c", "d", "e"}) {
            auto result = fs.getObject(v);
            ASSERT_TRUE(result);
            EXPECT_EQ(*result, val);
        };
        fs.removeObject("c");
        EXPECT_TRUE(fs.count() == 4);
        EXPECT_FALSE(fs.getObject("c"));
    }
}
}  // namespace cma
