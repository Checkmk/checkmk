def libxml2_local_repo(name):
    native.new_local_repository(
        name = name,
        build_file = "@//omd/packages/libxml2:BUILD",
        path = "/usr",
    )
