#!groovy

/// file: package_helper.groovy

/// distro-package as well as source-package jobs need agent updater binaries
/// built the same way.
/// This file gathers the magic to accomplish this, in orde to make it re-usable
///
/// Please note that the content in here badly written and full of hard-coded
/// values which should not be here. If that gets on `master`, it should be gotten
/// rid of as soon as possible

/// Returns the Jenkins 'branch folder' of the currently running job, either with or without
/// the 'Testing/..' prefix
/// So "Testing/bla.blubb/checkmk/2.4.0/some_job" will result in
/// "Testing/bla.blubb/checkmk/2.4.0" or "checkmk/2.4.0"
def branch_base_folder(with_testing_prefix) {
    def project_name_components = currentBuild.fullProjectName.split("/").toList();
    def checkmk_index = project_name_components.indexOf('checkmk');
    if (with_testing_prefix) {
        return project_name_components[0..checkmk_index + 1].join('/');
    }
    return project_name_components[checkmk_index..checkmk_index + 1].join('/');
}

def provide_agent_binaries(version, edition, disable_cache, bisect_comment) {
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
            relative_job_name: "${branch_base_folder(with_testing_prefix=false)}/builders/build-linux-agent-updater",
            /// no Linux agent updaters for raw edition..
            condition: true, // edition != "raw",  // FIXME!
            dependency_paths: [
                "agents",
                "non-free/cmk-update-agent"
            ],
            install_cmd: """\
                # check-mk-agent-*.{deb,rpm}
                cp *.deb *.rpm ${checkout_dir}/agents/
                # artifact file flags are not being kept - building a tar would be better..
                install -m 755 -D cmk-agent-ctl* mk-sql -t ${checkout_dir}/agents/linux/
                if [ "${edition}" != "raw" ]; then
                    echo "edition is ${edition} => copy Linux agent updaters"
                    install -m 755 -D cmk-update-agent* -t ${checkout_dir}/non-free/cmk-update-agent/
                fi
                """.stripIndent(),
        ],
        "winagt-build": [
            // NOTE: We're stripping of "Testing/..." if present, because
            //       Windows can't handle long folder names so we take the absolute
            //       (production) jobs to build our upstream stuff (both Linux and
            //       Windows for consistency).
            //       As 'soon' as this problem does not exist anymore we could run
            //       relatively from 'builders/..'
            relative_job_name: "${branch_base_folder(with_testing_prefix=false)}/winagt-build",
            dependency_paths: [
                "agents/wnx",
                "agents/windows",
                "packages/host/cmk-agent-ctl",
                "packages/host/mk-sql",
            ],
            install_cmd: """\
                cp \
                    check_mk_agent-64.exe \
                    check_mk_agent.exe \
                    check_mk_agent.msi \
                    check_mk_agent_unsigned.msi \
                    cmk-agent-ctl.exe \
                    check_mk.yml \
                    check_mk.user.yml \
                    OpenHardwareMonitorLib.dll \
                    OpenHardwareMonitorCLI.exe \
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
            relative_job_name: "${branch_base_folder(with_testing_prefix=false)}/winagt-build-modules",
            dependency_paths: [
                "agents/modules/windows",
            ],
            install_cmd: """\
                cp \
                    ./*.cab \
                    ${checkout_dir}/agents/windows/
                """.stripIndent(),
        ],
    ];

    def artifacts_base_dir = "tmp_artifacts";

    upstream_job_details.collect { job_name, details ->
        if ( ! details.get("condition", true) ) {
            return;
        }
        upstream_build(
            relative_job_name: details.relative_job_name,
            build_params: [
                DISABLE_CACHE: disable_cache,
                VERSION: version,
            ],
            build_params_no_check: [
                CIPARAM_BISECT_COMMENT: bisect_comment,
            ],
            dependency_paths: details.dependency_paths,
            no_venv: true,          // run ci-artifacts call without venv
            omit_build_venv: true,  // do not check or build a venv first
            dest: "${artifacts_base_dir}/${job_name}",
        );
        dir("${checkout_dir}/${artifacts_base_dir}/${job_name}") {
            sh(details.install_cmd);
        }
    }

    /// Cleanup
    sh("""
        # needed only because upstream_build() only downloads relative
        # to `base-dir` which has to be `checkout_dir`
        rm -rf ${checkout_dir}/${artifacts_base_dir}
        rm -rf ${checkout_dir}/agents/windows_tmp ${checkout_dir}/agents_tmp
    """);
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
