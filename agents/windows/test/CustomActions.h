#include <tuple>
#include "gmock/gmock.h"
#include "gtest/gtest.h"

ACTION_TEMPLATE(SetCharBuffer, HAS_1_TEMPLATE_PARAMS(unsigned, uIndex),
                AND_1_VALUE_PARAMS(data)) {
    // Courtesy of Microsoft: A function takes a char** param
    // but is declared as taking char* (>sigh<)
    *reinterpret_cast<char **>(std::get<uIndex>(args)) = data;
}
