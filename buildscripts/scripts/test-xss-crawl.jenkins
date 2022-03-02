def NODE
def DOCKER_TAG_DEFAULT
def BRANCH
withFolderProperties{
    NODE = env.BUILD_NODE
    DOCKER_TAG_DEFAULT = env.DOCKER_TAG_FOLDER
    BRANCH = env.BRANCH
}

properties([
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
    pipelineTriggers([cron("0 3 * * *")]),
])

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
            versioning = load 'buildscripts/scripts/lib/versioning.groovy'
            docker_util = load 'buildscripts/scripts/lib/docker_util.groovy'
            integration = load 'buildscripts/scripts/lib/integration.groovy'
            // ID of docker group on the node
            DOCKER_GROUP_ID = docker_util.get_docker_group_id()
        }
        try {
            integration.build(
                DOCKER_GROUP_ID: DOCKER_GROUP_ID,
                DISTRO_LIST: ["ubuntu-20.04"],
                EDITION: "enterprise",
                VERSION: "daily",
                DOCKER_TAG: versioning.select_docker_tag(versioning.get_branch(scm), "", DOCKER_TAG_DEFAULT),
                MAKE_TARGET: "test-xss-crawl-docker",
                BRANCH: BRANCH,
            )
        }catch(Exception e) {
            notify.notify_error(e)
        } finally {
            stage('archive crawler report') {
                xunit([JUnit(
                    deleteOutputFiles: true,
                    failIfNotNew: true,
                    pattern: "**/crawl.xml",
                    skipNoTestFiles: false,
                    stopProcessingIfError: true
                )])
            }
        }
    }
}
