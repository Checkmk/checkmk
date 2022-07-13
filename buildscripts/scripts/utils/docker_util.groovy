#!groovy

load("${checkout_dir}/buildscripts/docker_image_aliases/helpers.groovy");

// Make sure the docker group from outside the container is added inside of the contaienr
get_docker_group_id = { it ->
    cmd_output("getent group docker | cut -d: -f3");
}

