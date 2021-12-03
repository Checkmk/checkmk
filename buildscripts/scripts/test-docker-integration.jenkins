properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
])

def NODE = ''
withFolderProperties{
    NODE = env.BUILD_NODE
}

properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
  parameters([
    string(name: 'EDITION', defaultValue: 'enterprise', description: 'Edition: raw, enterprise or managed' ),
    string(name: 'VERSION', defaultValue: 'daily', description: 'Version: "daily" builds current git state of the branch. You also can specify a git tag here.' ),
  ])
])

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
            versioning = load 'buildscripts/scripts/lib/versioning.groovy'
            upload = load 'buildscripts/scripts/lib/upload_artifacts.groovy'
        }
    }
    
    try {
        node (NODE) {
            def PACKAGE_DIR = WORKSPACE + "/packages"
            def CMK_VERSION = versioning.get_cmk_version(scm, params.VERSION)

            stage('cleanup old versions') {
                sh("rm -rf \"${PACKAGE_DIR}\"")
            }

            upload.download_deb(INTERNAL_DEPLOY_DEST, INTERNAL_DEPLOY_PORT, CMK_VERSION, "${PACKAGE_DIR}/${CMK_VERSION}", EDITION, "buster")
            upload.download_source_tar(INTERNAL_DEPLOY_DEST, INTERNAL_DEPLOY_PORT, CMK_VERSION, "${PACKAGE_DIR}/${CMK_VERSION}", EDITION)

            stage('test cmk-docker integration') {
                dir ('tests') {
                    sh "make test-docker-docker EDITION='$EDITION' VERSION='$CMK_VERSION'"
                }
            }
        }
    } catch(Exception e) {
        notify.notify_error(e)
    }
}
