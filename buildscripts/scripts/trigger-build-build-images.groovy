#!groovy

/// file: trigger-build-build-images.groovy

void main() {
    check_job_parameters([
        "BUILD_IMAGE_WITHOUT_CACHE",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "OVERRIDE_DISTROS",
        "PUBLISH_IMAGES",
    ]);

    check_environment_variables([
        "ARTIFACT_STORAGE",
        "NEXUS_ARCHIVES_URL",
    ]);

    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);

    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def publish_images = params.PUBLISH_IMAGES == true;
    def publish_special_images = params.PUBLISH_SPECIAL_IMAGES_WITH_CUSTOM_GIT_REF;
    def vers_tag = params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD ?: versioning.get_docker_tag(checkout_dir);

    def all_distros = [];
    def selected_distros = [];

    if ("${params.CUSTOM_GIT_REF}" == "") {
        // if the build is started without a specific CUSTOM_GIT_REF (default case) publish the special images
        publish_special_images = true;
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        all_distros = versioning.get_distros(override: "all")
        selected_distros = versioning.get_distros(
            edition: "all",
            use_case: "all",
            override: params.OVERRIDE_DISTROS
        );
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............. │${all_distros}│
        |branch_version:........... │${branch_version}│
        |selected_distros:......... │${selected_distros}│
        |publish_images:........... │${publish_images}│
        |publish_special_images:... │${publish_images}│
        |safe_branch_name:......... │${safe_branch_name}│
        |vers_tag:................. │${vers_tag}│
        |===================================================
        """.stripMargin());

    def build_images = ["testing-image"];
    for (distro in all_distros) {
        if (distro in selected_distros) {
            build_images += distro;
        }
    }
    if (publish_special_images) {
        build_images += [
            "minimal-alpine-bash-git",
            "minimal-alpine-python-checkmk",
            "minimal-ubuntu-checkmk",
        ];
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder:.. │${checkout_dir}│
        |build_images:........ │${build_images}│
        |safe_branch_name:.... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    def stages = build_images.collectEntries { distro ->
        [("${distro}") : {
            smart_stage(
                name: "Trigger ${distro} build image build",
                raiseOnError: true,
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    force_build: force_build,
                    relative_job_name: "${branch_base_folder}/builders/build-build-image",
                    build_params: [
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: vers_tag,
                        CUSTOM_GIT_REF: effective_git_ref,
                        DISTRO: distro,
                        PUBLISH_IMAGES: publish_images,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
