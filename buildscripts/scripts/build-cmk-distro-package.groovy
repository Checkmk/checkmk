#!groovy

/// file: build-cmk-distro-package.groovy

/// Builds a distribution package (.rpm, .dep, etc.) for a given edition/distribution
/// at a given git hash

// groovylint-disable MethodSize
void main() {
    check_job_parameters([
        ["EDITION", true],
        ["DISTRO", true],
        ["VERSION", true],
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISABLE_CACHE",
        // TODO: Rename to FAKE_AGENT_ARTIFACTS -> we're also faking the linux updaters now
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def omd_env_vars = [
        "DEBFULLNAME='Checkmk Team'",
        "DEBEMAIL='feedback@checkmk.com'",
    ];

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def branch_base_folder = package_helper.branch_base_folder(false);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def checkout_hash = checkout_commit_id.substring(0, 6);
    def workspace_hash = String.format("%06x", WORKSPACE.hashCode());
    def container_name = "build-cmk-package-${distro}-${edition}-${workspace_hash}-${checkout_hash}";

    def bazel_log_prefix = "bazel_log_";

    def causes = currentBuild.getBuildCauses();
    def triggerd_by = "";
    for (cause in causes) {
        if (cause.upstreamProject != null) {
            triggerd_by += cause.upstreamProject + "/" + cause.upstreamBuild + "\n";
        }
    }
    def package_type = distro_package_type(distro);
    // groovylint-disable-next-line UnusedVariable
    def package_name = "";

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |cmk_version:.............. │${cmk_version}│
        |safe_branch_name:......... │${safe_branch_name}│
        |omd_env_vars:............. │${omd_env_vars}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |container_name:........... │${container_name}│
        |triggerd_by:.............. │${triggerd_by}│
        |package_type:............. │${package_type}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    if (params.CIPARAM_OVERRIDE_BUILD_NODE == "fips") {
        // Builds can not be done on FIPS node
        error("Package builds can not be done on FIPS node");
    }

    stage("Prepare workspace") {
        container("minimal-container") {
            dir("${checkout_dir}") {
                sh("""
                    make buildclean
                    find . -name *.pth -delete
                """);
                if (disable_cache) {
                    sh("""
                        rm -rf remote.bazelrc
                    """)
                }
                versioning.configure_checkout_folder(edition, cmk_version);
            }
        }
    }

    def stages = [
        "Build BOM": {
            def build_instance = null;
            def artifacts_base_dir = "tmp_artifacts";

            smart_stage(
                name: "Build BOM",
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-bom",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: version,
                        EDITION: edition,
                        DISABLE_CACHE: disable_cache,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    dest: "${artifacts_base_dir}",
                );
            }

            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: true,
            ) {
                // copyArtifacts seems not to work with k8s
                sh("""
                    # needed only because upstream_build() only downloads relative
                    # to `base-dir` which has to be `checkout_dir`
                    cp ${checkout_dir}/${artifacts_base_dir}/omd/* ${checkout_dir}/omd
                """);
            }
        },
    ];

    if (!params.FAKE_WINDOWS_ARTIFACTS) {
        stages += package_helper.provide_agent_binaries(
            version: version,
            cmk_version: cmk_version,
            edition: edition,
            disable_cache: disable_cache,
            bisect_comment: params.CIPARAM_BISECT_COMMENT,
            artifacts_base_dir: "tmp_artifacts",
        );
    } else {
        smart_stage(name: 'Fake agent binaries') {
            dir("${checkout_dir}") {
                sh("scripts/fake-artifacts");
            }
        }
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    package_helper.cleanup_provided_agent_binaries("tmp_artifacts");

    stage("Build package") {
        def lock_label = "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}";
        if (kubernetes_inherit_from != "UNSET") {
            lock_label = "bzl_lock_k8s";
        }

        lock(label: lock_label, quantity: 1, resource : null) {
            dir("${checkout_dir}") {
                // supplying the registry explicitly might not be needed but it looks like
                // image.inside() will first try to use the image without registry and only
                // if that didn't work falls back to the fully qualified name
                inside_container(
                    image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}"),
                    pull: true,
                    args: [
                        "--name ${container_name}",
                        " --hostname ${distro}",
                    ],
                ) {
                    versioning.print_image_tag();

                    withCredentials([
                        usernamePassword(
                            credentialsId: 'nexus',
                            passwordVariable: 'NEXUS_PASSWORD',
                            usernameVariable: 'NEXUS_USERNAME'),
                    ]) {
                        /// Don't use withEnv, see
                        /// https://issues.jenkins.io/browse/JENKINS-43632
                        def license_flag = ""
                        if (edition == "community") {
                            license_flag = '--//:repo_license="gpl"'
                        }
                        sh("""
                            bazel build \
                                --cmk_version=${cmk_version} \
                                --cmk_edition=${edition} \
                                ${license_flag} \
                                --execution_log_json_file="${checkout_dir}/deps_install.json" \
                        //omd:${package_type}_${edition}
                        """);
                        sh("cp --no-preserve=mode ${checkout_dir}/bazel-bin/omd/check-mk*.${package_type} ${checkout_dir}");
                    }
                    package_name = cmd_output("ls check-mk-${edition}-${cmk_version}*.${package_type}");
                    if (!package_type) {
                        error("No package 'check-mk-${edition}-${cmk_version}*.${package_type}' found in ${checkout_dir}");
                    }
                }
            }
        }
    }

    stage("Parse cache hits") {
        inside_container(
            image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}"),
        ) {
            bazel_logs.try_parse_bazel_execution_log(distro, checkout_dir, bazel_log_prefix);
        }
    }

    stage("Archive stuff") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "*.deb, *.rpm, *.cma, ${bazel_log_prefix}*, omd/bill-of-materials.json, trace_profile.json",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
