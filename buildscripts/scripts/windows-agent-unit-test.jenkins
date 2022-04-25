def FOLDER_ID = currentBuild.fullProjectName.split('/')[0]

properties([
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
    pipelineTriggers([triggers: [upstream(upstreamProjects: "${FOLDER_ID}/windows-agent-build", threshold: hudson.model.Result.SUCCESS)]]),
])

node('win_master_agent_unit') {
    stage('git checkout') {
        checkout(scm)
        windows = load 'buildscripts/scripts/lib/windows.groovy'
    }
    windows.build(
        TARGET: 'test_unit'
    )
}
