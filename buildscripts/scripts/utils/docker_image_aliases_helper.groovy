#!groovy

/// file: docker_image_aliases_helper.groovy

resolve_docker_image_alias = { alias_name ->
    // same as docker.build("build-image:${env.BUILD_ID}",
    //   "--pull ${WORKSPACE}/git/buildscripts/docker_image_aliases/${alias_name}")
    return cmd_output(
        "${checkout_dir}/buildscripts/docker_image_aliases/resolve.py ${alias_name}"
    ).replaceAll("[\r\n]+", "");
}

docker_image_from_alias = { alias_name ->
    return docker.image(resolve_docker_image_alias(alias_name));
}

docker_reference_image = { ->
    dir("${checkout_dir}") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            return docker.image(
                cmd_output("VERBOSE=1 PULL_BASE_IMAGE=1 ${checkout_dir}/defines/dev-images/reference-image-id")
            );
        }
    }
}

/// Returns some string from @image we can use to separate folders by distro
image_distro = { image ->
    /// Careful: while `docker.image(<NAME>).inside()` inside a `withRegistry` block will
    /// first try to run a container from @NAME _without_ registry first and then retry
    /// with the registry prefixed, `image.imageName()` will _allways_ be prefixed with
    /// the registry (even if it's a SHA).
    /// So having both the image name with _and_ without the registry on the same system
    /// should be avoided in general.
    def result = cmd_output("""
        docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' ${image.imageName()} | grep '^DISTRO=' | cut -d'=' -f2
    """) ?: cmd_output("""
        docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' ${image.id} | grep '^DISTRO=' | cut -d'=' -f2
    """);
    if (! result) {
        throw new Exception("Could not read .Config.Env from ${image.id}");
    }
    return result;
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

    def reference_repo_dir = cmd_output("""
        if [ -f ${checkout_dir}/.git/objects/info/alternates ]; then \
            dirname \$(cat ${checkout_dir}/.git/objects/info/alternates);\
        fi
     """);

    def image = args.image ?: docker_reference_image();
    def privileged = args.get("priviliged", false).asBoolean();
    def init = args.get("init", false).asBoolean();
    def pull = args.get("pull", false).asBoolean();
    def mount_reference_repo = args.get("mount_reference_repo", true).asBoolean();
    def mount_credentials = args.get("mount_credentials", false).asBoolean();
    def set_docker_group_id = args.get("set_docker_group_id", false).asBoolean();
    def create_cache_folder = args.get("create_cache_folder", true).asBoolean();
    def mount_host_user_files = args.get("mount_host_user_files", true).asBoolean();
    def run_args = args.args == null ? [] : args.args;

    // calling `image_distro()` has to be done inside `withRegistry` in order to
    // have `image.imageName()` contain the registry
    docker.withRegistry(DOCKER_REGISTRY, "nexus") {
        /// we don't just use `--pull always` here, because we also need it for `image_distro()`
        if (pull && args.image) {
            args.image.pull();
        }
        // We need to separate the mounts into the container distro-wise, at least for the following tools
        // - pipenv pip's wheel cache does not separate its cache in terms of platform/distro, see:
        // https://github.com/pypa/pip/issues/5453
        // - artifacts built under omd are distro dependend
        def container_shadow_workspace = "${WORKSPACE}/container_shadow_workspace_ci/${image_distro(image)}";
        def run_args_str = (
            run_args
            + (init ? ["--init"] : [])
            + (set_docker_group_id ? ["--group-add=${get_docker_group_id()}"] : [])
            + (args.ulimit_nofile ? ["--ulimit nofile=${args.ulimit_nofile}:${args.ulimit_nofile}"] : [])
            + (privileged ? ["-v /var/run/docker.sock:/var/run/docker.sock"] : [])
            + ["-v \"${container_shadow_workspace}/home:${env.HOME}\""]
            + (mount_credentials ? ["-v ${env.HOME}/.cmk-credentials:${env.HOME}/.cmk-credentials"] : [])
            + (mount_host_user_files ? ["-v /etc/passwd:/etc/passwd:ro -v /etc/group:/etc/group:ro"] : [])
            + ((mount_reference_repo && reference_repo_dir) ? ["-v ${reference_repo_dir}:${reference_repo_dir}:ro"] : [])
            + (create_cache_folder ? ["-v \"${container_shadow_workspace}/home_cache:${env.HOME}/.cache\""] : [])
            + ["-v \"${container_shadow_workspace}/checkout_cache:${checkout_dir}/.cache\""]
        ).join(" ");
        /// We have to make sure both, the source directory and (if applicable) the target
        /// directory inside an already mounted parent directory (here: /home/<USER>)
        /// exist, since otherwise they will be created with root ownership by
        /// poor Docker daemon.
        sh("""
            # BEGIN COMMON CODE with run-in-docker.sh

            mkdir -p "${container_shadow_workspace}/home"
            touch "${container_shadow_workspace}/home/.cmk-credentials"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${checkout_dir}")"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${env.WORKSPACE}")"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${env.WORKSPACE}/checkout_tmp")"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${env.WORKSPACE_TMP}")"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${reference_repo_dir}")"

            # not needed every time, but easier done unconditionally
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${env.WORKSPACE}/dependencyscanner")"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${env.WORKSPACE}/dependencyscanner_tmp")"

            # create mount dirs for $HOME/.cache (not to confuse with <checkout_dir>/.cache)
            mkdir -p "${container_shadow_workspace}/home_cache"
            mkdir -p "${container_shadow_workspace}/home/.cache"

            # create mount dirs for <checkout_dir>/.cache
            mkdir -p "${checkout_dir}/.cache"
            mkdir -p "${container_shadow_workspace}/checkout_cache"
            mkdir -p "${container_shadow_workspace}/home/\$(realpath -s --relative-to="${env.HOME}" "${checkout_dir}/.cache")"

            # probably not needed, but kept here because things are somehow working..
            mkdir -p "${checkout_dir}/shared_cargo_folder"

            # END COMMON CODE with run-in-docker.sh
        """);
        println("inside_container(image=${image} docker_args: ${run_args_str})");
        image.inside(run_args_str) {
            body();
        }
    }
}
