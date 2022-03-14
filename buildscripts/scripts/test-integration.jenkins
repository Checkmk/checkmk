def NODE
def DISTRO_LIST_DEFAULT
def DOCKER_TAG_DEFAULT
def BRANCH
withFolderProperties{
    NODE = env.BUILD_NODE
    DISTRO_LIST_DEFAULT = env.DISTRO_LIST
    DOCKER_TAG_DEFAULT = env.DOCKER_TAG_FOLDER
    BRANCH = env.BRANCH
}

def DOCKER_GROUP_ID

properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
  parameters([
    string(name: 'DISTROS', defaultValue: DISTRO_LIST_DEFAULT, description: 'List of targeted distros' ),
    string(name: 'EDITION', defaultValue: 'enterprise', description: 'Edition: raw, enterprise or managed' ),
    string(name: 'VERSION', defaultValue: 'daily', description: 'Version: "daily" builds current git state of the branch. You also can specify a git tag here.' ),
    string(name: 'DOCKER_TAG', defaultValue: '', description: 'Custom docker tag to use for this build. Leave empty for default' )
  ])
])

// TODO: Duplicate code (sync buildscripts/scripts/integration-daily-master.jenkins)
DISTRO_LIST = DISTROS.split(' ');
// CMK-1705: SLES-15 is missing xinitd and should therefore not be tested
DISTRO_LIST = DISTRO_LIST - ['sles-15']
// Testing CMA is not needed
DISTRO_LIST = DISTRO_LIST - ['cma']

currentBuild.description = '\nVersion: ' + VERSION + '\nEdition: ' + EDITION + '\nDistros: ' + DISTRO_LIST

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
            versioning = load 'buildscripts/scripts/lib/versioning.groovy'
            docker_util = load 'buildscripts/scripts/lib/docker_util.groovy'
            integration= load 'buildscripts/scripts/lib/integration.groovy'
            // ID of docker group on the node
            DOCKER_GROUP_ID = docker_util.get_docker_group_id()
    
        }
        try {
            integration.build(
                DOCKER_GROUP_ID: DOCKER_GROUP_ID,
                DISTRO_LIST: DISTRO_LIST,
                EDITION: EDITION,
                VERSION: VERSION,
                DOCKER_TAG: versioning.select_docker_tag(versioning.get_branch(scm), DOCKER_TAG, DOCKER_TAG_DEFAULT),
                MAKE_TARGET: "test-integration-docker",
                BRANCH: BRANCH,
            )
        }catch(Exception e) {
            notify.notify_error(e)
        }
    }
}
