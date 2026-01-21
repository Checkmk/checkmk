#!groovy

/// file: package_helper.groovy

/// distro-package as well as source-package jobs need agent updater binaries
/// built the same way.
/// This file gathers the magic to accomplish this, in orde to make it re-usable

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

/// Returns the Jenkins 'branch folder' of the currently running job, either with or without
/// the 'Testing/..' prefix
/// So "Testing/bla.blubb/checkmk/2.4.0/some_job" will result in
/// "Testing/bla.blubb/checkmk/2.4.0" or "checkmk/2.4.0"
String branch_base_folder(with_testing_prefix) {
    def project_name_components = currentBuild.fullProjectName.split("/").toList();
    def checkmk_index = project_name_components.indexOf('checkmk');
    if (with_testing_prefix) {
        return project_name_components[0..checkmk_index + 1].join('/');
    }
    return project_name_components[checkmk_index..checkmk_index + 1].join('/');
}

LinkedHashMap<String, List> directory_sha256sum(directories) {
    return directories.collectEntries({ path ->
        [("${path}".toString()): cmd_output("sha256sum <(find ${path} -type f -exec sha256sum {} \\; | sort) | cut -d' ' -f1")]
    });
}

static LinkedHashMap<String, List> dependency_paths_mapping() {
    return [
        "build-linux-agent-updater": [
            "agents",
            "non-free/packages/cmk-update-agent",
        ],
        "build-mk-oracle": [
            "packages/mk-oracle",
            "requirements/rust/host"
        ],
        "winagt-build": [
            "agents",
            "packages/cmk-agent-ctl",
            "packages/mk-sql",
            "third_party/asio",
            "third_party/fmt",
            "third_party/googletest",
            "third_party/openhardwaremonitor",
            "third_party/simpleini",
            "third_party/yaml-cpp",
        ],
        "winagt-build-modules": [
            "agents/modules/windows",
        ],
    ];
}

LinkedHashMap<String, List> dependency_paths_hashes() {
    dir("${checkout_dir}") {
        return dependency_paths_mapping().collectEntries({ job_name, paths ->
            [("${job_name}".toString()) : {
                def all_directory_hash_map = directory_sha256sum(paths);
                def all_directory_hash = all_directory_hash_map.collect { k, v -> "${k}=${v}" }.join('-');
                return all_directory_hash
          }()]
        });
    }
}

/* groovylint-disable MethodSize */
void provide_agent_binaries(Map args) {
    // always download and move artifacts unless specified differently
    def move_artifacts = args.move_artifacts == null ? true : args.move_artifacts.asBoolean();
    def all_dependency_paths_hashes = dependency_paths_hashes();
    def test_binaries_only = args.test_binaries_only == null ? false : true;

    // This _should_ go to an externally maintained file (single point of truth), see
    // https://jira.lan.tribe29.com/browse/CMK-13857
    // and https://review.lan.tribe29.com/c/check_mk/+/67387
    // For now it's nearly JSON like and can be treated as such.
    def upstream_job_details = [
        "build-linux-agent-updater": [
            // NOTE: We're stripping of "Testing/..." if present, because
            //       Windows can't handle long folder names so we take the absolute
            //       (production) jobs to build our upstream stuff (both Linux and
            //       Windows for consistency).
            //       As 'soon' as this problem does not exist anymore we could run
            //       relatively from 'builders/..'
            relative_job_name: "${branch_base_folder(false)}/builders/build-linux-agent-updater",
            /// no Linux agent updaters for community edition..
            condition: ! test_binaries_only,
            dependency_paths_hash: all_dependency_paths_hashes["build-linux-agent-updater"],
            additional_build_params: [],
            install_cmd: """\
                # check-mk-agent-*.{deb,rpm}
                cp *.deb *.rpm ${checkout_dir}/agents/
                # artifact file flags are not being kept - building a tar would be better..
                install -m 755 -D cmk-agent-ctl* mk-sql -t ${checkout_dir}/agents/linux/
                if [ "${args.edition}" != "community" ]; then
                    echo "edition is ${args.edition} => copy Linux agent updater binary"
                    install -m 755 -D cmk-update-agent -t ${checkout_dir}/non-free/packages/cmk-update-agent/
                fi
                """.stripIndent(),
        ],
        "build-mk-oracle-aix-solaris": [
            relative_job_name: "${branch_base_folder(false)}/builders/build-mk-oracle-on-aix-and-solaris",
            dependency_paths_hash: all_dependency_paths_hashes["build-mk-oracle"],
            additional_build_params: [],
            condition: ! test_binaries_only,
            install_cmd: """\
                cp mk-oracle.{aix,solaris} ${checkout_dir}/omd/packages/mk-oracle/
                """.stripIndent(),
        ],
        "build-mk-oracle-rhel8": [
            relative_job_name: "${branch_base_folder(false)}/builders/build-cmk-package",
            dependency_paths_hash: all_dependency_paths_hashes["build-mk-oracle"],
            condition: ! test_binaries_only,
            additional_build_params: [
                PACKAGE_PATH: "packages/mk-oracle",
                DISTRO: "almalinux-8",
                FILE_ARCHIVING_PATTERN: "mk-oracle*",
                // do not add line breaks here. ci-artifacts might not find a match
                // groovylint-disable-next-line LineLength
                COMMAND_LINE: """bazel build --cmk_version=${args.cmk_version} mk-oracle; cp \$(bazel info workspace)/\$(bazel cquery --output=files mk-oracle) \$(bazel info workspace)""",
            ],
            install_cmd: """\
                cp mk-oracle ${checkout_dir}/omd/packages/mk-oracle/mk-oracle.rhel8
                """.stripIndent(),
        ],
        "build-mk-oracle-rhel8-component-test": [
            relative_job_name: "${branch_base_folder(false)}/builders/build-cmk-package",
            dependency_paths_hash: all_dependency_paths_hashes["build-mk-oracle"],
            condition: test_binaries_only,
            additional_build_params: [
                PACKAGE_PATH: "packages/mk-oracle",
                DISTRO: "almalinux-8",
                FILE_ARCHIVING_PATTERN: "test_ora_sql_test",
                // do not add line breaks here. ci-artifacts might not find a match
                // groovylint-disable-next-line LineLength
                COMMAND_LINE: """bazel build //packages/mk-oracle:mk-oracle-lib-test-external; cp \$(bazel info workspace)/\$(bazel cquery --output=files //packages/mk-oracle:mk-oracle-lib-test-external_tests/test_ora_sql_test) \$(bazel info workspace)"""
            ],
            install_cmd: """\
                cp test_ora_sql_test ${checkout_dir}/packages/mk-oracle/
                """.stripIndent(),
        ],
        "winagt-build": [
            // NOTE: We're stripping of "Testing/..." if present, because
            //       Windows can't handle long folder names so we take the absolute
            //       (production) jobs to build our upstream stuff (both Linux and
            //       Windows for consistency).
            //       As 'soon' as this problem does not exist anymore we could run
            //       relatively from 'builders/..'
            relative_job_name: "${branch_base_folder(false)}/winagt-build",
            dependency_paths_hash: all_dependency_paths_hashes["winagt-build"],
            condition: ! test_binaries_only,
            additional_build_params: [],
            install_cmd: """\
                cp \
                    mk-oracle.exe \
                    ${checkout_dir}/omd/packages/mk-oracle/
                cp \
                    check_mk_agent-64.exe \
                    check_mk_agent.exe \
                    check_mk_agent.msi \
                    check_mk_agent_unsigned.msi \
                    cmk-agent-ctl.exe \
                    check_mk.yml \
                    check_mk.user.yml \
                    mk-sql.exe \
                    robotmk_ext.exe \
                    windows_files_hashes.txt \
                    ${checkout_dir}/agents/windows/
                (
                    cd ${checkout_dir}/agents/windows
                    ${checkout_dir}/buildscripts/scripts/create_unsign_msi_patch.sh \
                        check_mk_agent.msi \
                        check_mk_agent_unsigned.msi \
                        unsign-msi.patch
                )
                """.stripIndent(),
        ],
        "winagt-build-modules": [
            // NOTE: We're stripping of "Testing/..." if present, because
            //       Windows can't handle long folder names so we take the absolute
            //       (production) jobs to build our upstream stuff (both Linux and
            //       Windows for consistency).
            //       As 'soon' as this problem does not exist anymore we could run
            //       relatively from 'builders/..'
            relative_job_name: "${branch_base_folder(false)}/winagt-build-modules",
            dependency_paths_hash: all_dependency_paths_hashes["winagt-build-modules"],
            condition: ! test_binaries_only,
            additional_build_params: [],
            install_cmd: """\
                cp \
                    ./*.cab \
                    ${checkout_dir}/agents/windows/
                """.stripIndent(),
        ],
    ];

    def stages = upstream_job_details.collectEntries { job_name, details ->
        [("${job_name}".toString()) : {
            def run_condition = details["condition"];
            def build_instance = null;

            if (! run_condition) {
                Utils.markStageSkippedForConditional("${job_name}");
            }

            smart_stage(
                name: job_name,
                condition: run_condition,
                raiseOnError: true,
            ) {
                def this_parameters = [
                    use_upstream_build: true,
                    relative_job_name: details.relative_job_name,
                    download: false,
                ];

                if (details.dependency_paths_hash) {
                    // if dependency_paths are specified these will be used as unique identifier
                    // CUSTOM_GIT_REF is handed over as well, but not activly checked by ci-artifacts
                    this_parameters += [
                        build_params: [
                            CIPARAM_PATH_HASH: details.dependency_paths_hash,
                            VERSION: args.version,
                            DISABLE_CACHE: args.disable_cache,
                        ] + details.additional_build_params,
                        build_params_no_check: [
                            CUSTOM_GIT_REF: effective_git_ref,
                            CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                            CIPARAM_BISECT_COMMENT: args.bisect_comment,
                        ],
                    ]
                } else {
                    this_parameters += [
                        build_params: [
                            CUSTOM_GIT_REF: effective_git_ref,
                            VERSION: args.version,
                            DISABLE_CACHE: args.disable_cache,
                        ] + details.additional_build_params,
                        build_params_no_check: [
                            CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                            CIPARAM_BISECT_COMMENT: args.bisect_comment,
                        ],
                    ]
                }

                if (move_artifacts) {
                    // specify to download artifacts to desired destination
                    this_parameters += [
                        download: true,
                        dest: "${args.artifacts_base_dir}/${job_name}",
                        no_remove_others: true, // do not delete other files in the dest dir
                    ];
                }
                build_instance = smart_build(this_parameters);
            }

            smart_stage(
                name: "Move artifacts around",
                condition: run_condition && build_instance && move_artifacts,
                raiseOnError: true,
            ) {
                // prevent "_tmp" directories created by the Jenkins groovy dir() command
                def install_cmd = "cd ${checkout_dir}/${args.artifacts_base_dir}/${job_name};";
                install_cmd += details.install_cmd;
                sh(install_cmd);
            }
        }]
    }

    return stages;
}

void cleanup_provided_agent_binaries(artifacts_base_dir) {
    /// Cleanup
    sh("""
        # needed only because upstream_build() only downloads relative
        # to `base-dir` which has to be `checkout_dir`
        rm -rf ${checkout_dir}/${artifacts_base_dir}
        rm -rf ${checkout_dir}/agents/windows_tmp ${checkout_dir}/agents_tmp
    """);
}

void sign_package(source_dir, package_path) {
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

void test_package(package_path, name, workspace, source_dir, cmk_version) {
    def junit_file = "junit-${name}.xml";
    try {
        sh("""
            PACKAGE_PATH=${package_path} \
            PYTEST_ADDOPTS='--junitxml=${workspace}/${junit_file}' \
            make -C '${source_dir}/tests' VERSION=${cmk_version} test-packaging
        """);
    } finally {
        step([
            $class: "JUnitResultArchiver",
            testResults: junit_file,
        ]);
    }
}

return this;
