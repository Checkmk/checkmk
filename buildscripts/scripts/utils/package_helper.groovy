#!groovy

/// file: package_helper.groovy

/// distro-package as well as source-package jobs need agent updater binaries
/// built the same way.
/// This file gathers the magic to accomplish this, in orde to make it re-usable
///
/// Please note that the content in here badly written and full of hard-coded
/// values which should not be here. If that gets on `master`, it should be gotten
/// rid of as soon as possible

def provide_agent_updaters(version, edition, disable_cache) {
    upstream_build(
        relative_job_name: "builders/build-linux-agent-updater",
        build_params: [
            DISABLE_CACHE: DISABLE_CACHE,
            VERSION: VERSION,
        ],
        // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
        dependency_paths: ["agents", "non-free/cmk-update-agent"],
        dest: "artifacts/build-linux-agent-updater",
    );
    dir("${checkout_dir}/artifacts/build-linux-agent-updater") {
        sh("find .");
        sh("""
            cp *.deb *.rpm ${checkout_dir}/agents/
            mkdir -p ${checkout_dir}/agents/linux
            # artifact file flags are not being kept - building a tar would be better..
            install -m 755 cmk-agent-ctl* mk-sql ${checkout_dir}/agents/linux/
        """);
        if (edition != "raw") {
            sh("install -m 755 cmk-update-agent* ${checkout_dir}/non-free/cmk-update-agent/");
        }
    }

    upstream_build(
        relative_job_name: "winagt-build",  // TODO: move to builders
        build_params: [
            DISABLE_CACHE: DISABLE_CACHE,
            VERSION: VERSION,
        ],
        // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
        dependency_paths: [
            "agents/wnx",
            "agents/windows",
            "packages/host/cmk-agent-ctl",
            "packages/host/mk-sql"
        ],
        dest: "artifacts/winagt-build",
    );
    dir("${checkout_dir}/artifacts/winagt-build") {
        sh("find .");
        // TODO: SPoT!!
        sh("""
           mkdir -p ${checkout_dir}/agents/windows
           cp \
            check_mk_agent-64.exe \
            check_mk_agent.exe \
            check_mk_agent.msi \
            check_mk_agent_unsigned.msi \
            check_mk.user.yml \
            OpenHardwareMonitorLib.dll \
            OpenHardwareMonitorCLI.exe \
            mk-sql.exe \
            robotmk_ext.exe \
            windows_files_hashes.txt \
            ${checkout_dir}/agents/windows/
        """);
    }
    dir("${checkout_dir}/agents/windows") {
        sh("""
            ${checkout_dir}/buildscripts/scripts/create_unsign_msi_patch.sh \
            check_mk_agent.msi check_mk_agent_unsigned.msi unsign-msi.patch
        """);
    }

    upstream_build(
        relative_job_name: "winagt-build-modules",  // TODO: move to builders
        build_params: [
            DISABLE_CACHE: DISABLE_CACHE,
            VERSION: VERSION,
        ],
        // TODO: SPoT!!, see https://jira.lan.tribe29.com/browse/CMK-13857
        dependency_paths: ["agents/modules/windows"],
        dest: "artifacts/winagt-build-modules",
    );
    dir("${checkout_dir}/agents/windows") {
        sh("find ${checkout_dir}/artifacts/winagt-build-modules");
        sh("cp ${checkout_dir}/artifacts/winagt-build-modules/*.cab .");
    }
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
