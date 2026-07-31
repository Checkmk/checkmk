#!groovy

/// file: windows.groovy

/// Assemble the CorrelationId sent along with every Azure artifact signing request.
///
/// Azure reports the value back in the signing diagnostics, so it tells us which CI job
/// triggered a signing request. The suffix is a shared secret, so that signing requests which did
/// not originate from our CI can be spotted in those diagnostics.
///
/// The caller binds `azure_artifact_signing_correlation_suffix` and must keep it bound for the
/// whole signing step: the Azure client prints its metadata (CorrelationId included) to stdout,
/// and Jenkins only masks the secret while its `withCredentials` block is open.
///
/// Quotes are stripped: on Windows agents `make print-%` echoes values wrapped in single quotes
/// (defines.make), which cmd.exe does not strip, so branch_name may arrive as e.g. '3.0.0'.
/// Azure's CorrelationId is an opaque tracking string.
String azure_signing_correlation_id(String branch_name) {
    return "${branch_name}_${env.AZURE_ARTIFACT_SIGNING_CORRELATION_SUFFIX}".replaceAll("['\"]", "");
}

def build(Map args) {
    def jenkins_base_folder = new File(currentBuild.fullProjectName).parent;    // groovylint-disable JavaIoPackageAccess
    def artifacts_dir = 'artefacts';

    dir(artifacts_dir) {
        stage("Download  artifacts") {
            if (args.TARGET == "test_integration") {
                copyArtifacts(
                    projectName: "${jenkins_base_folder}/winagt-build",
                )
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
                "python-3.cab"] :
            (args.TARGET == "agent_with_sign") || (args.TARGET == "agent_with_sign_azure") ? [
                "agents/wnx",
                // The deprecated_unused_param's have to be present or the script will fail.
                "call run.cmd --all " +
                    "${args.TARGET == 'agent_with_sign_azure' ? '--sign-azure' : '--sign'} " +
                    "deprecated_unused_param1 deprecated_unused_param2",
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
                } catch (Exception exc) {    // groovylint-disable CatchException
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

return this;
