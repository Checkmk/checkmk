def glib_local_repo(name):
    native.new_local_repository(
        name = name,
        build_file = "@//omd/packages/glib:BUILD",
        path = "/usr",
    )
