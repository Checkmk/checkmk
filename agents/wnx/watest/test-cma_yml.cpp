// test-cap.cpp:
// Installation of cap files

#include "pch.h"

#include "common/cma_yml.h"

namespace cma::yml {

TEST(CmaYml, GetValNothing) {
    YAML::Node y_null;
    ASSERT_NO_THROW(GetVal<int>(y_null, "global", "number"));
}
TEST(CmaYml, GetVal) {
    auto y = YAML::Load("global:\n  number: 2\n  string: 'str'");

    EXPECT_EQ(*GetVal<int>(y, "global", "number"), 2);
    EXPECT_FALSE(GetVal<int>(y, "global", "numbers"));
    EXPECT_EQ(GetVal(y, "global", "number", 5), 2);
    EXPECT_EQ(GetVal(y, "global", "numbers", 5), 5);
    EXPECT_EQ(*GetVal<std::string>(y, "global", "string"), "str");
    EXPECT_FALSE(GetVal<std::string>(y, "global", "string__"));
    EXPECT_EQ(GetVal(y, "global", "string", std::string("s")), "str");
    EXPECT_EQ(GetVal(y, "global", "string__", std::string("s")), "s");

    auto y1 = GetNode(y, "global");
    EXPECT_TRUE(y1.IsMap());

    EXPECT_EQ(*GetVal<int>(y1, "number"), 2);

    EXPECT_EQ(GetVal(y1, "number", 3), 2);
    EXPECT_EQ(GetVal(y1, "number__", 3), 3);
    EXPECT_FALSE(GetNode(y1, "global"));
    EXPECT_EQ(GetVal(y1, "string", std::string("s")), "str");
    EXPECT_EQ(GetVal(y1, "string__", std::string("s")), "s");
}

}  // namespace cma::yml
