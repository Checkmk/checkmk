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

docker_reference_image = { ->
    // this hack was introduced as there is no reference image in 2.3.0
    return docker_image_from_alias("IMAGE_TESTING");
}

/// This function is the CI-equivalent to scripts/run-in-docker.sh. It should do
/// the same as closely as possible. So if you're editing one of us please also
/// update the other one, too!
inside_container = {Map arg1=[:], Closure arg2 ->
    // strangely providing a default value for @args does not work as expected.
    // If no value got provided the provided body is taken as @args.
    // In _script console_ however @arg1 will be [:] (the expected default arg)
    // if no argument was provided.
    // So we handle both cases here, setting default value for @args manually
    def (args, body) = arg2 == null ? [[:], arg1] : [arg1, arg2];

    def image = args.image ?: docker_reference_image();
    def privileged = args.get("priviliged", false).asBoolean();
    def init = args.get("init", false).asBoolean();
    def mount_reference_repo = args.get("mount_reference_repo", true).asBoolean();
    def mount_credentials = args.get("mount_credentials", false).asBoolean();
    def set_docker_group_id = args.get("set_docker_group_id", false).asBoolean();
    def run_args = args.args == null ? [] : args.args;
    def run_args_str = (
        run_args
        + (init ? ["--init"] : [])
        + (set_docker_group_id ? ["--group-add=${get_docker_group_id()}"] : [])
        + (args.ulimit_nofile ? ["--ulimit nofile=${args.ulimit_nofile}:${args.ulimit_nofile}"] : [])
        + (privileged ? ["-v /var/run/docker.sock:/var/run/docker.sock"] : [])
        + (mount_credentials ? ["-v ${env.HOME}/.cmk-credentials:${env.HOME}/.cmk-credentials"] : [])
        + (mount_reference_repo ? ["${mount_reference_repo_dir}"] : [])
    ).join(" ");

    println("inside_container(image=${image} docker_args: ${run_args_str})");
    docker.withRegistry(DOCKER_REGISTRY, "nexus") {
        image.inside(run_args_str) {
            body();
        }
    }
}
