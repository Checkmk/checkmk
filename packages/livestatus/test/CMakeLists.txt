set(CMAKE_VERBOSE_MAKEFILE ON)

add_executable(test test.cc)
target_include_directories(test PUBLIC ../include)
target_compile_features(test PRIVATE cxx_std_17)
target_compile_options(test PUBLIC -Wall -Wextra -Werror -fPIC -gdwarf-4 -std=c++17)
target_link_options(test PRIVATE -static)
target_link_libraries(test PRIVATE livestatus pthread stdc++)
