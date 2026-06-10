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
        "FAKE_ARTIFACTS",
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
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def omd_env_vars = [
        "DEBFULLNAME='Checkmk Team'",
        "DEBEMAIL='feedback@checkmk.com'",
    ];

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);

    // FIXME
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);

    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def docker_tag = versioning.select_docker_tag(
        params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
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
    def license_flag = edition == "community" ? '--//:repo_license="gpl"' : "";
    def fake_artifacts = params.FAKE_ARTIFACTS ? "--//:use_faked_artifacts=true" : "";
    def enable_compression = versioning.is_official_release(cmk_version_rc_aware) ? "" : "--//:low_zstd_compression=true";
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    print(
        """
        |===== CONFIGURATION ===============================
        |distro:................... │${distro}│
        |edition:.................. │${edition}│
        |cmk_version:.............. │${cmk_version}│
        |safe_branch_name:......... │${safe_branch_name}│
        |force_build:.............. │${force_build}│
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

    def stages = [:];

    if (!params.FAKE_ARTIFACTS) {
        stages += package_helper.provide_agent_binaries(
            version: version,
            cmk_version: cmk_version,
            edition: edition,
            disable_cache: disable_cache,
            bisect_comment: params.CIPARAM_BISECT_COMMENT,
            artifacts_base_dir: "tmp_artifacts",
            fake_artifacts: params.FAKE_ARTIFACTS,
        );
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    package_helper.cleanup_provided_agent_binaries("tmp_artifacts");

    stage("Build package") {
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
                    artifacts_helper.withHotCache([
                        download_dest: "~",
                        remove_existing_cache: true,
                        target_name: "build-omd-${package_type}",
                        cache_prefix: versioning.distro_code(),
                        // When we mount the shared repository cache, we won't pack the repository cache under ~/.cache
                        // into the hot cache and therefore we dont need to consider WORKSPACE and MODULE.bazel.lock
                        files_to_consider: [
                            '.bazelversion',
                            'requirements.txt',
                            'bazel/tools/package.json',
                        ] + (env.MOUNT_SHARED_REPOSITORY_CACHE == "1" ? [] : ['WORKSPACE', 'MODULE.bazel.lock']),
                        disable_hot_cache: env.USE_STASHED_BAZEL_FOLDER_CMK_DISTRO_BUILD == "0",
                    ]) {
                        sh("""
                            bazel build \
                                ${fake_artifacts} \
                                ${enable_compression} \
                                --cmk_version=${cmk_version} \
                                --cmk_edition=${edition} \
                                ${license_flag} \
                                --execution_log_json_file="${checkout_dir}/deps_install.json" \
                        //omd:${package_type} \
                        //omd/dependency_management:generate_bom_csv \
                        //omd/dependency_management:bill_of_materials_renamed
                        """);
                    }
                    sh("cp --no-preserve=mode ${checkout_dir}/bazel-bin/omd/check-mk*.${package_type} ${checkout_dir}");
                    sh("cp ${checkout_dir}/bazel-bin/omd/dependency_management/bill-of-materials.{json,csv} ${checkout_dir}");
                }
                package_name = cmd_output("ls check-mk-${edition}-${cmk_version}*.${package_type}");
                if (!package_type) {
                    error("No package 'check-mk-${edition}-${cmk_version}*.${package_type}' found in ${checkout_dir}");
                }
            }
        }
    }

    stage("Validate package") {
        catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
            dir("${checkout_dir}") {
                inside_container(
                    image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}"),
                ) {
                    def bazel_testlogs = sh(script: "bazel info bazel-testlogs", returnStdout: true).trim();
                    def log_src = "${bazel_testlogs}/omd/validate_${package_type}/test.log";
                    def report_src = "${bazel_testlogs}/omd/validate_${package_type}/test.outputs/report.json";
                    try {
                        sh("""
                            bazel test \
                                ${fake_artifacts} \
                                ${enable_compression} \
                                --cmk_version=${cmk_version} \
                                --cmk_edition=${edition} \
                                ${license_flag} \
                        //omd:validate_${package_type}
                        """);
                    } finally {
                        sh("cp --no-preserve=mode ${log_src} ${checkout_dir}/package_validator.log");
                        sh("cp --no-preserve=mode ${report_src} ${checkout_dir}/package_validator.report.json");
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
                    artifacts: [
                        "*.deb, *.rpm, *.cma, ${bazel_log_prefix}*",
                        "bill-of-materials.json, bill-of-materials.csv, trace_profile.json",
                        "package_validator.log",
                        "package_validator.report.json",
                    ].join(", "),
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
