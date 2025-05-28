#!groovy

/// file: build-cmk-packages.groovy

/// Build the distribution packages (.rpm, .dep, etc.) for a given edition of
/// Checkmk and a given set of distributions.
/// Optionally publish those packages to the Checkmk download page.
/// Used in two contexts: in build chain and in Testbuild

/// Important note:
/// This script is also used for the "Testbuild" job which uses a slightly
/// different scenario: packages are built for a subset of distros only and
/// OMD package and Python optimizations are disabled.

/* groovylint-disable MethodSize */
def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "SKIP_DEPLOY_TO_WEBSITE",
        "DEPLOY_TO_WEBSITE_ONLY",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
        "USE_CASE",
    ]);

    check_environment_variables([
        "INTERNAL_DEPLOY_URL",
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
        "NODE_NAME",
        "JOB_BASE_NAME",
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
        "BAZEL_CACHE_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def bazel_logs = load("${checkout_dir}/buildscripts/scripts/utils/bazel_logs.groovy");

    def bazel_log_prefix = "bazel_log_";

    def (jenkins_base_folder, use_case, omd_env_vars, upload_path_suffix) = (
        env.JOB_BASE_NAME == "testbuild" ? [
            new File(currentBuild.fullProjectName).parent,
            "testbuild",
            /// Testbuilds: Do not use our build cache to ensure we catch build related
            /// issues. And disable python optimizations to execute the build faster
            ["NEXUS_BUILD_CACHE_URL="],
            "testbuild/",
        ] : [
            new File(new File(currentBuild.fullProjectName).parent).parent,
            VERSION == "daily" ? params.USE_CASE : "release",
            [],
            "",
        ]);

    def all_distros = versioning.get_distros(override: "all");
    def distros = versioning.get_distros(edition: edition, use_case: use_case, override: OVERRIDE_DISTROS);

    def deploy_to_website = !params.SKIP_DEPLOY_TO_WEBSITE && !jenkins_base_folder.startsWith("Testing");

    def agent_list = get_agent_list(EDITION);

    def safe_branch_name = versioning.safe_branch_name();

    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    /// Get the ID of the docker group from the node(!). This must not be
    /// executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();

    def upload_path = "${INTERNAL_DEPLOY_DEST}${upload_path_suffix}";

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............. │${all_distros}│
        |distros:.................. │${distros}│
        |deploy_to_website:........ │${deploy_to_website}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |omd_env_vars:............. │${omd_env_vars}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |docker_group_id:.......... │${docker_group_id}│
        |upload_path:.............. │${upload_path}│
        |docker_registry_no_http:.. │${docker_registry_no_http}│
        |checkout_dir:............. │${checkout_dir}│
        |agent_list:............... │${agent_list}│
        |jenkins_base_folder:...... │${jenkins_base_folder}│
        |===================================================
        """.stripMargin());

    currentBuild.description += (
        """
        |Building for the following distros:<br>
        |${distros}<br>
        |Edition: ${EDITION}<br>
        |Fake artifacts: ${FAKE_WINDOWS_ARTIFACTS}<br>
        |""".stripMargin());

    // TODO This has to go into a dedicated job, soon!
    if (params.DEPLOY_TO_WEBSITE_ONLY) {
        // This stage is used only by bauwelt/bw-release in order to publish an already built release
        stage('Deploying previously build version to website only') {
            inside_container(ulimit_nofile: 1024) {
                artifacts_helper.deploy_to_website(cmk_version_rc_aware);
                artifacts_helper.cleanup_rc_candidates_of_version(cmk_version_rc_aware);
            }
        }
        return;
    }

    stage("Cleanup") {
        cleanup_directory("${WORKSPACE}/versions");
        cleanup_directory("${WORKSPACE}/agents");
        sh("rm -rf ${WORKSPACE}/${bazel_log_prefix}*");
        inside_container(ulimit_nofile: 1024) {
            dir("${checkout_dir}") {
                sh("make buildclean");
                versioning.configure_checkout_folder(EDITION, cmk_version);
            }
        }
    }

    /// NOTE: the images referenced in the next step can only be considered
    ///       up to date if the same node is being used as for the
    ///       `build-build-images` job. For some reasons we can't just pull the
    ///       latest image though, see
    ///       https://review.lan.tribe29.com/c/check_mk/+/34634
    ///       Anyway this whole upload/download mayhem hopfully evaporates with
    ///       bazel..
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        distros.each { distro ->
            docker.image("${distro}:${docker_tag}").pull();
        }
    }

    def win_project_name_id = -1;
    def win_py_project_name_id = -1;
    def win_project_name = "${jenkins_base_folder}/winagt-build";
    def win_py_project_name = "${jenkins_base_folder}/winagt-build-modules";

    conditional_stage("Build agent artifacts fast", !params.FAKE_WINDOWS_ARTIFACTS) {
        inside_container(ulimit_nofile: 1024) {
            dir("${checkout_dir}") {
                // Initialize our virtual environment before parallelization
                sh("make .venv");

                win_project_name_id = get_valid_build_id(win_project_name);
                win_py_project_name_id = get_valid_build_id(win_py_project_name);
            }
        }
    }

    // TODO iterate over all agent variants and put the condition per edition
    //      in the conditional_stage
    def agent_builds = agent_list.collectEntries { agent ->
        [("agent ${agent}") : {
                conditional_stage("Build Agent for ${agent}", !params.FAKE_WINDOWS_ARTIFACTS) {
                    if (agent == "windows") {
                        copyArtifacts(
                            projectName: win_project_name,
                            selector: specific(win_project_name_id), // buildNumber shall be a string
                            target: "agents",
                            fingerprintArtifacts: true
                        );
                        copyArtifacts(
                            projectName: win_py_project_name,
                            selector: specific(win_py_project_name_id), // buildNumber shall be a string
                            target: "agents",
                            fingerprintArtifacts: true
                        );
                    } else {
                        /// must take place in $WORKSPACE since we need to
                        /// access $WORKSPACE/agents
                        inside_container(
                            set_docker_group_id: true,
                            ulimit_nofile: 1024,
                            priviliged: true,
                        ) {
                            build_linux_agent_updater(agent, EDITION, branch_version, docker_registry_no_http);
                        }
                    }
                }
            }]
    }
    parallel agent_builds;

    // With the current bazelization this job regularly breaks. Lets be tolerant...
    // This should be mandatory as soon as we enter the beta phase!
    catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
        // TODO creates stages - put them on top level
        create_and_upload_bom(WORKSPACE, branch_version, VERSION);
    }

    inside_container(ulimit_nofile: 2048) {
        // TODO creates stages
        create_source_package(WORKSPACE, checkout_dir, cmk_version);

        def SOURCE_PACKAGE_NAME = get_source_package_name("${checkout_dir}", EDITION, cmk_version);
        def BUILD_SOURCE_PACKAGE_PATH = "${checkout_dir}/${SOURCE_PACKAGE_NAME}";
        def node_version_dir = "${WORKSPACE}/versions";
        def FINAL_SOURCE_PACKAGE_PATH = "${node_version_dir}/${cmk_version_rc_aware}/${SOURCE_PACKAGE_NAME}";

        stage('Copy source package') {
            copy_source_package(BUILD_SOURCE_PACKAGE_PATH, FINAL_SOURCE_PACKAGE_PATH);
        }
        stage('Cleanup source package') {
            cleanup_source_package(checkout_dir, FINAL_SOURCE_PACKAGE_PATH);
        }
        stage("Test source package") {
            test_package(FINAL_SOURCE_PACKAGE_PATH, "source", WORKSPACE, checkout_dir, cmk_version);
        }
        stage("Upload source package") {
            artifacts_helper.upload_via_rsync(
                "${node_version_dir}",
                "${cmk_version_rc_aware}",
                SOURCE_PACKAGE_NAME,
                "${upload_path}",
                INTERNAL_DEPLOY_PORT,
            );
            assert_no_dirty_files(checkout_dir);
        }
    }

    def package_builds = distros.collectEntries { distro ->
        [("distro ${distro}") : {
            // The following node call allocates a new workspace for each
            // DISTRO.
            //
            // Note: Do it inside the first node block to ensure all distro
            // workspaces start with a fresh one. Otherwise one of the node
            // calls would reuse the workspace of the source package step.
            //
            // The DISTRO workspaces will then be initialized with the contents
            // of the first workspace, which contains the prepared git repo.

            /// For now make sure, we're on the SAME node (but different WORKDIR)
            /// To make the builds run across different nodes we have to
            /// use `stash` to distribute the source
            node(env.NODE_NAME) {
                /// $WORKSPACE is different now - we must not use variables
                /// like $checkout_dir which are based on the parent
                /// workspace accidentally (and
                assert "${WORKSPACE}/checkout" != checkout_dir;

                def distro_dir = "${WORKSPACE}/checkout";

                lock(label: 'bzl_lock_' + env.NODE_NAME.split("\\.")[0].split("-")[-1], quantity: 1, resource : null) {
                    inside_container(
                        image: docker.image("${distro}:${docker_tag}"),
                        args: [
                            "--ulimit nofile=16384:32768",
                            "-v ${checkout_dir}:${checkout_dir}:ro",
                            "--hostname ${distro}",
                        ],
                        init: true,
                    ) {
                        stage("${distro} initialize workspace") {
                            cleanup_directory("${WORKSPACE}/versions");
                            sh("rm -rf ${distro_dir}");
                            sh("rsync -a ${checkout_dir}/ ${distro_dir}/");
                            sh("rm -rf ${distro_dir}/bazel_execution_log*");
                        }

                        stage("${distro} build package") {
                            withCredentials([
                                usernamePassword(
                                    credentialsId: 'nexus',
                                    passwordVariable: 'NEXUS_PASSWORD',
                                    usernameVariable: 'NEXUS_USERNAME'),
                                usernamePassword(
                                    credentialsId: 'bazel-caching-credentials',
                                    /// BAZEL_CACHE_URL must be set already, e.g. via Jenkins config
                                    passwordVariable: 'BAZEL_CACHE_PASSWORD',
                                    usernameVariable: 'BAZEL_CACHE_USER'),
                            ]) {
                                versioning.print_image_tag();
                                build_package(distro_package_type(distro), distro_dir, omd_env_vars);
                            }
                        }
                        sh("""echo ==== ${distro} =====
                        ps wauxw
                        """);

                        stage("Parse bazel execution logs") {
                            bazel_logs.try_parse_bazel_execution_log(distro, distro_dir, bazel_log_prefix)
                        }
                    }
                }

                inside_container(
                    args: [
                        "-v ${checkout_dir}:${checkout_dir}:ro",
                    ],
                    ulimit_nofile: 1024,
                ) {
                    def package_name = versioning.get_package_name(distro_dir, distro_package_type(distro), EDITION, cmk_version);
                    def build_package_path = "${distro_dir}/${package_name}";
                    def node_version_dir = "${WORKSPACE}/versions";
                    def final_package_path = "${node_version_dir}/${cmk_version_rc_aware}/${package_name}";

                    stage("${distro} sign package") {
                        sign_package(distro_dir, build_package_path);
                    }

                    stage("${distro} test package") {
                        test_package(build_package_path, distro, WORKSPACE, distro_dir, cmk_version);
                    }

                    stage("${distro} copy package") {
                        copy_package(build_package_path, distro, final_package_path);
                    }

                    stage("${distro} upload package") {
                        artifacts_helper.upload_via_rsync(
                            "${node_version_dir}",
                            "${cmk_version_rc_aware}",
                            "${package_name}",
                            "${upload_path}",
                            INTERNAL_DEPLOY_PORT,
                        );
                    }
                }

                stage("${distro} workspace sanity check") {
                    check_for_workspace_sanity();
                }
            }
        }]
    }
    parallel package_builds;

    stage("Plot cache hits") {
        bazel_logs.try_plot_cache_hits(bazel_log_prefix, distros);
    }

    conditional_stage('Upload', !jenkins_base_folder.startsWith("Testing")) {
        currentBuild.description += (
            """ |${currentBuild.description}<br>
                |<p><a href='${INTERNAL_DEPLOY_URL}/${upload_path_suffix}${cmk_version}'>Download Artifacts</a></p>
                |""".stripMargin());
        def exclude_pattern = versioning.get_internal_artifacts_pattern();
        inside_container(ulimit_nofile: 1024) {
            assert_no_dirty_files(checkout_dir);
            artifacts_helper.download_version_dir(
                upload_path,
                INTERNAL_DEPLOY_PORT,
                cmk_version_rc_aware,
                "${WORKSPACE}/versions/${cmk_version_rc_aware}",
                "*",
                "all packages",
                exclude_pattern,
            );
            /// BOM shall have a unique name, see CMK-16483
            sh("""
                cp ${checkout_dir}/omd/bill-of-materials.json ${WORKSPACE}/versions/${cmk_version_rc_aware}/check-mk-${params.EDITION}-${cmk_version_rc_aware}-bill-of-materials.json
            """);
            artifacts_helper.upload_version_dir(
                "${WORKSPACE}/versions/${cmk_version_rc_aware}", WEB_DEPLOY_DEST, WEB_DEPLOY_PORT, EXCLUDE_PATTERN=exclude_pattern);
            if (deploy_to_website) {
                artifacts_helper.deploy_to_website(cmk_version_rc_aware);
            }
        }
    }
}

def get_agent_list(edition) {
    return (edition == "raw" ?
        ["windows"] :
        ["au-linux-64bit", "au-linux-32bit", "windows"]);
}

def build_linux_agent_updater(agent, edition, branch_version, registry) {
    print("FN build_linux_agent_updater(agent=${agent}, edition=${edition}, branch_version=${branch_version}, registry=${registry})");

    def suffix = agent == "au-linux-32bit" ? "-32" : "";

    withCredentials([
        usernamePassword(
            credentialsId: 'nexus',
            passwordVariable: 'NEXUS_PASSWORD',
            usernameVariable: 'NEXUS_USERNAME')
    ]) {
        dir("${checkout_dir}/non-free/cmk-update-agent") {
            def cmd = "BRANCH_VERSION=${branch_version} DOCKER_REGISTRY_NO_HTTP=${registry} ./make-agent-updater${suffix}";
            on_dry_run_omit(LONG_RUNNING, "RUN ${cmd}") {
                sh(cmd);
            }
        }
    }
    dir("${WORKSPACE}/agents") {
        def cmd = "cp ${checkout_dir}/non-free/cmk-update-agent/cmk-update-agent${suffix} .";
        on_dry_run_omit(LONG_RUNNING, "RUN ${cmd}") {
            sh(cmd);
        }
    }
}

def create_and_upload_bom(workspace, branch_version, version) {
    print("FN create_and_upload_bom(workspace=${workspace}, branch_version=${branch_version}, version=${version})");

    dir("${workspace}/dependencyscanner") {
        def scanner_image;
        def bom_path = "${checkout_dir}/omd/bill-of-materials.json";

        stage('Prepare BOM') {
            on_dry_run_omit(LONG_RUNNING, "Prepare BOM") {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: 'refs/heads/master']],
                    browser: [
                        $class: 'GitWeb',
                        repoUrl: 'https://review.lan.tribe29.com/git/?p=dependencyscanner.git'
                    ],
                    userRemoteConfigs: [
                        [
                            credentialsId: '058f09c4-21c9-49ae-b72b-0b9d2f465da6',
                            url: 'ssh://jenkins@review.lan.tribe29.com:29418/dependencyscanner'
                        ]
                    ],
                ]);
                scanner_image = docker.build("dependencyscanner", "--tag dependencyscanner .");
            }
        }
        stage('Create BOM') {
            on_dry_run_omit(LONG_RUNNING, "Create BOM") {
                inside_container(
                    image: scanner_image,
                    args: ["-v ${checkout_dir}:${checkout_dir}"], // why?!
                ) {
                    sh("""python3 -m dependencyscanner \
                    --stage prod \
                    --outfile '${bom_path}' \
                    --research_file researched_2.3.0.yml \
                    --license_cache license_cache_2.3.0.json \
                    '${checkout_dir}'""");
                }
            }
        }
        stage('Upload BOM') {
            withCredentials([string(
                    credentialsId: 'dtrack',
                    variable: 'DTRACK_API_KEY')]) {
                withEnv(["DTRACK_URL=${DTRACK_URL}"]) {
                    on_dry_run_omit(LONG_RUNNING, "Upload BOM") {
                        inside_container(
                            image: scanner_image,
                            args: [
                                "-v ${checkout_dir}:${checkout_dir}", // why?!
                                "--env DTRACK_URL,DTRACK_API_KEY",
                            ],
                        ) {
                            sh("""scripts/upload-bom \
                            --bom-path '${bom_path}' \
                            --project-name 'Checkmk ${branch_version}' \
                            --project-version '${version}'""");
                        }
                    }
                }
            }
        }
    }
}

def create_source_package(workspace, source_dir, cmk_version) {
    print("FN create_source_package(workspace=${workspace}, source_dir=${source_dir}, cmk_version=${cmk_version})");
    // The vanilla agent RPM would normally be created by "make dist", which is
    // called in the next stage, but we need to create and sign it. For this
    // reason we explicitly execute the RPM build in this separate step. The
    // "make dist" will then use the signed RPM.
    dir("${source_dir}/agents") {
        sh("make rpm");
    }

    stage("Vanilla agent sign package") {
        sign_package(source_dir, "${source_dir}/agents/check-mk-agent-${cmk_version}-1.noarch.rpm");
    }

    stage("Create source package") {
        def agents_dir = "${workspace}/agents";
        def signed_msi = "check_mk_agent.msi";
        def unsigned_msi = "check_mk_agent_unsigned.msi";
        def target_dir = "agents/windows";
        def scripts_dir = "${checkout_dir}/buildscripts/scripts";
        def patch_script = "create_unsign_msi_patch.sh";
        def patch_file = "unsign-msi.patch";
        def ohm_files = "OpenHardwareMonitorLib.dll,OpenHardwareMonitorCLI.exe";
        def ext_files = "robotmk_ext.exe";
        def mk_sql = "mk-sql.exe";
        def hashes_file = "windows_files_hashes.txt";
        def artifacts = [
            "check_mk_agent-64.exe",
            "check_mk_agent.exe",
            "${signed_msi}",
            "${unsigned_msi}",
            "check_mk.user.yml",
            "python-3.cab",
            "${ohm_files}",
            "${ext_files}",
            "${mk_sql}",
            "${hashes_file}",
        ].join(",");

        if (params.FAKE_WINDOWS_ARTIFACTS) {
            sh("mkdir -p ${agents_dir}");
            if(EDITION != 'raw') {
                sh("touch ${agents_dir}/cmk-update-agent");
                sh("touch ${agents_dir}/cmk-update-agent-32");
            }
            sh("touch ${agents_dir}/{${artifacts}}");
        }
        dir("${checkout_dir}") {
            if(EDITION != 'raw') {
                sh("cp ${agents_dir}/cmk-update-agent non-free/cmk-update-agent/");
                sh("cp ${agents_dir}/cmk-update-agent-32 non-free/cmk-update-agent/");
            }
            sh("cp ${agents_dir}/{${artifacts}} ${target_dir}");
            sh("${scripts_dir}/${patch_script} ${target_dir}/${signed_msi} ${target_dir}/${unsigned_msi} ${target_dir}/${patch_file}");
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')
            ]) {
                sh('make dist || cat /root/.npm/_logs/*-debug.log');
            }
        }
    }
}

def get_source_package_name(source_dir, edition, cmk_version) {
    print("FN get_source_package_name(source_dir=${source_dir}, edition=${edition}, cmk_version=${cmk_version})");
    dir("${source_dir}") {
        return (cmd_output("ls check-mk-${edition}-${cmk_version}.c?e*.tar.gz")
                ?: error("Found no source package path matching ${source_dir}/check-mk-${edition}-${cmk_version}.c?e*.tar.gz"));
    }
}

def cleanup_source_package(source_dir, package_path) {
    print("FN cleanup_source_package(source_dir=${source_dir}, package_path=${package_path})");
    sh("${source_dir}/buildscripts/scripts/cleanup-source-archives.sh ${package_path}");
}

def copy_source_package(package_path, archive_path) {
    print("FN copy_source_package(package_path=${package_path}, archive_path=${archive_path})");
    sh("mkdir -p \$(dirname ${archive_path})");
    sh("cp ${package_path} ${archive_path}");
}

def build_package(package_type, build_dir, env) {
    print("FN build_package(package_type=${package_type}, build_dir=${build_dir}, env=${env})");
    dir(build_dir) {
        // TODO: THIS MUST GO AWAY ASAP
        // Backgroud:
        // * currently we're building protobuf during source packaging (make dist) in IMAGE_TESTING.
        // * then, we're simply rsyncing the whole workspace in the different distro workspaces (including the protoc)
        // * as protobuf exists then in the intermediate_install, it will be used (and not obtained from a correct
        //   cache key, including DISTRO information...)
        // * if we then build under an old distro, we get linker issues
        // * so as long as we don't have the protobuf build bazelized, we need to manually clean it up here.
        sh("rm -fr omd/build/intermediate_install/protobuf*");
        sh("rm -fr omd/build/stamps/protobuf*");


        // used withEnv(env) before, but sadly Jenkins does not set 0 length environment variables
        // see also: https://issues.jenkins.io/browse/JENKINS-43632
        try {
            def env_str = env.join(" ");
            sh("${env_str} DEBFULLNAME='Checkmk Team' DEBEMAIL='feedback@checkmk.com' make -C omd ${package_type}");
        } finally {
            sh("""
                cd '${checkout_dir}/omd'
                echo 'Maximum heap size:'
                bazel info peak-heap-size
                echo 'Server log:'
                cat \$(bazel info server_log)
                echo '### PROCESSES ###'
                ps -axjf
                bazel shutdown
            """);
        }
    }
}

def copy_package(package_path, distro, archive_path) {
    print("FN copy_package(package_path=${package_path}, distro=${distro}, archive_path=${archive_path})");
    sh("mkdir -p \$(dirname ${archive_path})");
    sh("cp '${package_path}' '${archive_path}'");
}

def sign_package(source_dir, package_path) {
    print("FN sign_package(source_dir=${source_dir}, package_path=${package_path})");
    withCredentials([file(
        credentialsId: "Check_MK_Release_Key",
        variable: "GPG_KEY",)]) {
        /// --batch is needed to awoid ioctl error
        sh("gpg --batch --import ${GPG_KEY}");
    }
    withCredentials([
        usernamePassword(
            credentialsId: "9d7aca31-0043-4cd0-abeb-26a249d68261",
            passwordVariable: "GPG_PASSPHRASE",
            usernameVariable: "GPG_USERNAME",)
    ]) {
        sh("${source_dir}/buildscripts/scripts/sign-packages.sh ${package_path}");
    }
}

def test_package(package_path, name, workspace, source_dir, cmk_version) {
    /* groovylint-disable LineLength */
    print("FN test_package(package_path=${package_path}, name=${name}, workspace=${workspace}, source_dir=${source_dir}, cmk_version=${cmk_version})");
    /* groovylint-enable LineLength */
    try {
        withEnv([
            "PACKAGE_PATH=${package_path}",
            "PYTEST_ADDOPTS='--junitxml=${workspace}/junit-${name}.xml'",
        ]) {
            sh("make -C '${source_dir}/tests' VERSION=${cmk_version} test-packaging");
        }
    } finally {
        step([
            $class: "JUnitResultArchiver",
            testResults: "junit-${name}.xml",
        ]);
    }
}

def get_valid_build_id(jobName) {
    /// In order to avoid unnessessary builds for the given job, we check if we
    /// can use a completed or currently running build instead.
    /// That's the case if the following requirements are met:
    /// - there _is_ a completed build
    /// - it's been successful
    /// - it's from same day
    /// - VERSION parameter matches with current build's
    /// - and must be one of 'git' or 'daily'
    /// Only in the special case if a job is triggered but still in the queue
    /// upstream_build can not find that job and will thereby trigger a new job

    show_duration("Build ${jobName}") {
        def currentBuildVersion = params.VERSION;
        def job = upstream_build(
            download: false,
            // force_build: currentBuildVersion in ["daily", "git"],
            relative_job_name: jobName,
            build_params: [
                VERSION: currentBuildVersion,
                CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
            ],
        );
        return "${job.number}";
    }
}

return this;
