// library for Windows builds
package lib

FOLDER_ID = currentBuild.fullProjectName.split('/')[0]

def build(Map args) {
    def ARTIFACTS_DIR = 'artefacts'
    def ARTIFACTS = ''
    if (args.TARGET == "test_integration" || args.TARGET == "test_unit") {
        download_artifacts("${FOLDER_ID}/windows-agent-build", ARTIFACTS_DIR)
    }

    stage("Windows ${args.TARGET} build") {
        // Windows integration test is the longest running test with kust under 3 min
        // No job should exceed 3*5 = 15 minutes
        timeout(time: 15, unit: 'MINUTES') {
            try {
                if (args.TARGET == "cached") {
                    bat 'cd agents\\modules\\windows && call build_the_module.cmd cached ' + args.CREDS + ' ' + args.CACHE_URL
                    ARTIFACTS = 'python-3.cab,python-3.4.cab'
                } else if (args.TARGET == "agent_with_sign") {
                    bat 'cd agents\\wnx && call build_release.cmd tribe29.pfx ' + args.PASSWORD
                    ARTIFACTS = "cmk-agent-ctl.exe,check_mk_agent-64.exe,check_mk_agent.exe,check_mk_agent.msi,check_mk_agent_unsigned.msi,check_mk.user.yml,check_mk.yml,watest32.exe,watest64.exe,unit_tests_results.zip"
                } else if (args.TARGET == "agent_no_sign") {
                    bat 'cd agents\\wnx && call build_release.cmd'
                    ARTIFACTS = "cmk-agent-ctl.exe,check_mk_agent-64.exe,check_mk_agent.exe,check_mk_agent.msi,check_mk.user.yml,check_mk.yml,watest32.exe,watest64.exe"
                } else if (args.TARGET == "cmk_agent_ctl_no_sign") {
                    bat 'cd agents\\cmk-agent-ctl && call cargo_build.cmd'
                } else if (args.TARGET == "test_unit") {
                    bat 'cd agents\\wnx && call call_unit_tests.cmd -*_Long:*Integration:*IntegrationExt:*Flaky'
                    ARTIFACTS = "unit_tests_results.zip"
                } else if (args.TARGET == "test_integration") {
                    bat 'cd agents\\wnx && call run_integration_tests.cmd all'
                    ARTIFACTS = "integration_tests_results.zip"
                } else if (args.TARGET == "test_build") {
                    bat 'cd agents\\wnx && call call_test_build.cmd'
                } else {
                    throw new Exception(args.TARGET + " is not known!")
                }
    
                if (ARTIFACTS != '') {
                   if (args.STASH_NAME == null ) {
                      archive_artifacts(ARTIFACTS, ARTIFACTS_DIR)
                   } else {
                      stash_artifacts(ARTIFACTS, args.STASH_NAME, ARTIFACTS_DIR)
                   }
                }
    
            } catch(ERROR) {
                mail(
                    to: WIN_DEV_MAIL,
                    cc: '', 
                    bcc: '', 
                    from: JENKINS_MAIL, 
                    replyTo: '', 
                    subject: "Win Error in $BUILD_URL",
                    body: """
                        The following Error appered in 
                        Build URL: $BUILD_URL \n
                    """
                        + ERROR.getMessage()
                )
                throw ERROR
            }
        }
    }
}

def download_artifacts(PROJECT_NAME, DIR) {
    stage('download artifacts') {
        dir(DIR) {
            script {
                step ([$class: 'CopyArtifact',
                projectName: "${FOLDER_ID}/windows-agent-build",
            ]);
            }
        }
    }
}

def archive_artifacts(ARTIFACTS, DIR) {
    dir(DIR) {
        archiveArtifacts ARTIFACTS
    }
}

def stash_artifacts(ARTIFACTS, STASH_NAME, DIR) {
    dir(DIR) {
       stash(
            name: STASH_NAME,
            includes: ARTIFACTS
        )
    }
}

return this
