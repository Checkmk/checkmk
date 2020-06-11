
#include "pch.h"
// INCLUDED IN PROJECT
// ../common;../../external/asio/asio/include;../../external/fmt/include;../../external/gtest/googletest/include;../../external/gtest/googletest;../../external/catch2/include
// DEFINED IN PROJECT
// ASIO_STANDALONE;ASIO_HEADER_ONLY;_WIN32_WINNT=0x0501;_SILENCE_CXX17_ALLOCATOR_VOID_DEPRECATION_WARNING;FMT_HEADER_ONLY;

// Compatibility with other headers
#define CATCH_CONFIG_DISABLE_MATCHERS
#define GTEST_DONT_DEFINE_FAIL 1
#define GTEST_DONT_DEFINE_SUCCEED 1

// Candidates to place in pch
#include <iostream>
#include <asio.hpp>
#include <fmt/format.h>
#include <gtest/gtest.h>
#include <gtest/gtest.h>
#include <catch.hpp>

int main() {
    std::cout << "Hello World!\n";
    fmt::print("Hello {}", "a");

    // gtest execution
    auto result = RUN_ALL_TESTS();
    return result;
}
