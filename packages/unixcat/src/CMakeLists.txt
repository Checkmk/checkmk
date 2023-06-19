set(unixcat_sources unixcat.cc)

add_executable(unixcat ${unixcat_sources})

set(lib_livestatus_include ${root_repo_dir}/packages/livestatus/include)

target_include_directories(unixcat PRIVATE ${lib_livestatus_include})

target_link_libraries(unixcat PRIVATE pthread)

target_compile_features(unixcat PUBLIC cxx_std_17)
