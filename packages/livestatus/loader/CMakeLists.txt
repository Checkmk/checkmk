set(CMAKE_VERBOSE_MAKEFILE ON)

add_executable(loader loader.cc)
target_include_directories(loader PUBLIC ../include)
target_compile_features(loader PRIVATE cxx_std_17)
target_compile_options(loader PUBLIC -Wall -Wextra -Werror -fPIC -O3 -gdwarf-4)
target_link_options(loader PRIVATE -static)
target_link_libraries(loader PRIVATE livestatus pthread stdc++)