#!groovy

/// file: windows.groovy

void build(Map args) {
    def jenkins_base_folder = new File(currentBuild.fullProjectName).parent;    // groovylint-disable JavaIoPackageAccess
    def artifacts_dir = 'artefacts';

    dir(artifacts_dir) {
        stage("Download artifacts") {
            if (args.TARGET == "test_integration") {
                copyArtifacts(
                    projectName: "${jenkins_base_folder}/winagt-build-modules",
                )
            }
        }
    }

    stage("Windows ${args.TARGET} build") {
        // Windows integration test is the longest running test with just under 3 min
        // No job should exceed 3*5 = 15 minutes

        def (subdir, command, artifacts) = (
            (args.TARGET == "cached") ? [
                "agents/modules/windows",
                "call build_the_module.cmd cached ${args.CREDS} ${args.CACHE_URL} ${args.DISABLE_CACHE}",
                "python-3.cab"] :
            (args.TARGET == "agent_with_sign") ? [
                "agents/wnx",
                // The deprecated_unused_param's have to be present or the script will fail.
                "call run.cmd --all --sign deprecated_unused_param1 deprecated_unused_param2",
                [
                    "cmk-agent-ctl.exe",
                    "check_mk_agent-64.exe",
                    "check_mk_agent.exe",
                    "check_mk_agent.msi",
                    "check_mk_agent_unsigned.msi",
                    "check_mk.user.yml",
                    "check_mk.yml",
                    "watest32.exe",
                    "watest64.exe",
                    "unit_tests_results.zip",
                    "robotmk_ext.exe",
                    "mk-oracle.exe",
                    "mk-sql.exe",
                    "windows_files_hashes.txt",
                ].join(",")] :
            (args.TARGET == "agent_no_sign") ? [
                "agents/wnx",
                "call run.cmd --all",
                [
                    "cmk-agent-ctl.exe",
                    "check_mk_agent-64.exe",
                    "check_mk_agent.exe",
                    "check_mk_agent.msi",
                    "check_mk.user.yml",
                    "check_mk.yml",
                    "watest32.exe",
                    "watest64.exe",
                ].join(",")] :
            (args.TARGET == "cmk_agent_ctl_no_sign") ? [
                "packages/cmk-agent-ctl",
                "call run.cmd --all",
                ""] :
            (args.TARGET == "mk_oracle_no_sign") ? [
                "packages/mk-oracle",
                "call run.cmd --all",
                "mk-oracle.exe"] :

            (args.TARGET == "mk_sql_no_sign") ? [
                "packages/mk-sql",
                "call run.cmd --all",
                "mk-sql.exe"] :

            (args.TARGET == "test_integration") ? [
                "agents/wnx",
                "call run_tests.cmd --component --integration",
                "integration_tests_results.zip"] :
            raise("${args.TARGET} is not known!")
        )

        dir(artifacts_dir) {
            for (artifact in artifacts.split(",")) {
                println("Removing may existing build output file ${artifact} from ${artifacts_dir}");
                try {
                    cmd_output("pwsh -c rm -Force ${artifact} -ErrorAction SilentlyContinue");
                }
                catch (Exception exc) {
                    println("FAILED TO DELETE FILE ${artifact} due to: ${exc}");
                }
            }
        }

        timeout(time: 60, unit: 'MINUTES') {
            dir(subdir) {
                bat(command);
            }
        }

        if (artifacts != '') {
            dir(artifacts_dir) {
                if (args.STASH_NAME == null ) {
                    show_duration("archiveArtifacts") {
                        archiveArtifacts(
                            artifacts: artifacts,
                            fingerprint: true,
                        );
                    }
                }
            }
        }
    }
}

return this;
