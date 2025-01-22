#!groovy

/// file: docker_util.groovy

load("${checkout_dir}/buildscripts/scripts/utils/docker_image_aliases_helper.groovy");

// Make sure the docker group from outside the container is added inside of the contaienr
get_docker_group_id = { it ->
    cmd_output("getent group docker | cut -d: -f3");
}
