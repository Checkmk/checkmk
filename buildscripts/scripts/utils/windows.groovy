#!groovy

/// file: windows.groovy

def build(Map args) {
    def jenkins_base_folder = new File(currentBuild.fullProjectName).parent;    // groovylint-disable JavaIoPackageAccess
    def artifacts_dir = 'artefacts';

    dir(artifacts_dir) {
        stage("Download  artifacts") {
            if (args.TARGET == "test_integration" || args.TARGET == "test_unit") {
                copyArtifacts(
                    projectName: "${jenkins_base_folder}/winagt-build",
                )
            }

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
                "call build_the_module.cmd cached ${args.CREDS} ${args.CACHE_URL}",
                "python-3.cab,python-3.4.cab"] :
            (args.TARGET == "agent_with_sign") ? [
                "agents/wnx",
                "call build_release.cmd checkmk.pfx ${args.PASSWORD}",
                "cmk-agent-ctl.exe,check_mk_agent-64.exe,check_mk_agent.exe,check_mk_agent.msi,check_mk_agent_unsigned.msi,check_mk.user.yml,check_mk.yml,watest32.exe,watest64.exe,unit_tests_results.zip,OpenHardwareMonitorLib.dll,OpenHardwareMonitorCLI.exe"] :
            (args.TARGET == "agent_no_sign") ? [
                 "agents/wnx",
                 "call build_release.cmd",
                 "cmk-agent-ctl.exe,check_mk_agent-64.exe,check_mk_agent.exe,check_mk_agent.msi,check_mk.user.yml,check_mk.yml,watest32.exe,watest64.exe"] :
            (args.TARGET == "cmk_agent_ctl_no_sign") ? [
                "packages/cmk-agent-ctl",
                "call run.cmd --all",
                 ""] :
            (args.TARGET == "test_unit") ? [
                 "agents/wnx",
                 "call call_unit_tests.cmd -*_Long:*Integration:*IntegrationExt:*Flaky",
                 "unit_tests_results.zip"] :
            (args.TARGET == "test_integration") ? [
                "agents/wnx",
                "call run_integration_tests.cmd all",
                 "integration_tests_results.zip"] :
            (args.TARGET == "test_build") ? [
                "agents/wnx",
                "call call_test_build.cmd",
                ""] :
            raise("${args.TARGET} is not known!")
        )

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
                } else {
                    stash(
                        name: args.STASH_NAME,
                        includes: artifacts
                    );
                }
            }
        }
    }
}

return this
