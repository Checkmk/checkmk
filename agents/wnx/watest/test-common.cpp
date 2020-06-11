// test-common.cpp:
// checking headers in common

#include "pch.h"

#include "common/yaml.h"

TEST(Common, YamlWrapperBase) {
    auto node = YAML::Load("xxx:\n  zzz: 5\n");
    ASSERT_TRUE(node[std::string("xxx")][std::string("zzz")].as<int>() == 5);
    ASSERT_TRUE(
        node[std::string_view("xxx")][std::string_view("zzz")].as<int>() == 5);
    ASSERT_FALSE(node.remove(std::string_view("___")));
    ASSERT_TRUE(node.remove(std::string_view("xxx")));
    ASSERT_FALSE(node.remove(std::string_view("xxx")));
}
