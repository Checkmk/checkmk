// test-cap.cpp:
// Installation of cap files

#include "pch.h"

#include "common/cma_yml.h"
#include <yaml-cpp/yaml.h>

namespace cma::yml {

TEST(CmaYml, All) {
    YAML::Node y_null;
    ASSERT_NO_THROW(GetVal<int>(y_null, "global", "number"));

    auto y = YAML::Load("global:\n  number: 2\n  string: 'str'");

    {
        auto x = GetVal<int>(y, "global", "number");
        EXPECT_TRUE(x);
        EXPECT_EQ(*x, 2);
    }

    {
        auto x = GetVal<int>(y, "global", "numbers");
        EXPECT_FALSE(x);
    }
    {
        auto x = GetVal(y, "global", "number", 5);
        EXPECT_EQ(x, 2);
    }
    {
        auto x = GetVal(y, "global", "numbers", 5);
        EXPECT_EQ(x, 5);
    }

    {
        auto x = GetVal<std::string>(y, "global", "string");
        EXPECT_TRUE(x);
        EXPECT_EQ(*x, "str");
    }

    {
        auto x = GetVal<std::string>(y, "global", "string__");
        EXPECT_FALSE(x);
    }
    {
        auto x = GetVal(y, "global", "string", std::string("s"));
        EXPECT_EQ(x, "str");
    }
    {
        auto x = GetVal(y, "global", "string__", std::string("s"));
        EXPECT_EQ(x, "s");
    }

    {
        auto y1 = GetNode(y, "global");
        EXPECT_TRUE(y1);
        EXPECT_TRUE(y1.IsMap());

        auto v = GetVal<int>(y1, "number");
        EXPECT_TRUE(v);
        EXPECT_EQ(*v, 2);

        auto val_hit = GetVal(y1, "number", 3);
        EXPECT_EQ(val_hit, 2);

        auto val_miss = GetVal(y1, "number__", 3);
        EXPECT_EQ(val_miss, 3);

        auto y2 = GetNode(y1, "global");
        EXPECT_FALSE(y2);

        auto str_hit = GetVal(y1, "string", std::string("s"));
        EXPECT_EQ(str_hit, "str");

        auto str_miss = GetVal(y1, "string__", std::string("s"));
        EXPECT_EQ(str_miss, "s");
    }
}

}  // namespace cma::yml
