enable_testing()

add_executable(test test.cc)

# Google Test
set(googletest_version googletest-9c332145b7)
FetchContent_Declare(
  googletest-omd
  URL ${CMAKE_SOURCE_DIR}/../../omd/packages/googletest/${googletest_version}.tar.gz
)
FetchContent_MakeAvailable(googletest-omd)
FetchContent_GetProperties(
  googletest-omd
  SOURCE_DIR src_dir
  BINARY_DIR bin_dir
  POPULATED done_var)
message("googletest src: " ${src_dir})
message("googletest bin: " ${bin_dir})
set(googletest_ext_include ${src_dir}/googletest/include)

target_include_directories(test PUBLIC ../include ${googletest_ext_include})
target_compile_features(test PRIVATE cxx_std_17)
target_link_options(test PRIVATE -rdynamic)
target_link_libraries(test PRIVATE livestatus pthread stdc++ GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(test)
