// library for Windows builds
package lib

def build(Map args) {
    def ARTIFACTS_DIR = 'artefacts'
    def ARTIFACTS = ''
    if (args.TARGET == "test_integration") {
        download_artifacts('cmk_master/windows-agent-build', ARTIFACTS_DIR)
    }

    stage("Windows ${args.TARGET} build") {
        try {
            if (args.TARGET == "module") {
                bat 'cd agents\\modules\\windows && call build_the_module.cmd python'
                ARTIFACTS = 'python-3.8.zip'
            } else if (args.TARGET == "cached") {
                bat 'cd agents\\modules\\windows && call build_the_module.cmd cached ' + args.CREDS + ' ' + args.CACHE_URL
                ARTIFACTS = 'python-3.8.zip'
            } else if (args.TARGET == "agent") {
                bat 'cd agents\\wnx && call build_release.cmd'
                ARTIFACTS = "check_mk_agent-64.exe,check_mk_agent.exe,check_mk_agent.msi,check_mk.user.yml"
            } else if (args.TARGET == "test_integration") {
                bat 'cd agents\\wnx && call call_integration_tests.cmd'
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

def download_artifacts(PROJECT_NAME, DIR) {
    stage('download artifacts') {
        dir(DIR) {
            script {
                step ([$class: 'CopyArtifact',
                projectName: 'cmk_master/windows-agent-build',
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
