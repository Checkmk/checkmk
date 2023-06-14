#!groovy

/// file: docker_image_aliases_helper.groovy

resolve_docker_image_alias = { alias_name ->
    // same as docker.build("build-image:${env.BUILD_ID}",
    //   "--pull ${WORKSPACE}/git/buildscripts/docker_image_aliases/IMAGE_TESTING")
    return cmd_output(
        "${checkout_dir}/buildscripts/docker_image_aliases/resolve.py ${alias_name}"
    ).replaceAll("[\r\n]+", "");
}


docker_image_from_alias = { alias_name ->
    return docker.image(resolve_docker_image_alias(alias_name));
}

