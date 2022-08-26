def main() {
    /*
    properties([
        pipelineTriggers([pollSCM('H/2 * * * *')])
    ])

    versioning = load 'buildscripts/scripts/utils/versioning.groovy'

    def TEST_IMAGE = docker.build("test-image:${env.BUILD_ID}", "--pull buildscripts/docker_image_aliases/IMAGE_TESTING")
    // The commands are executed with the 1001:1000 UID:GID (non-root).
    // This is the UID of the jenkins user on the node which does not exist
    // in the container. For the moment this does not look like a problem.
    // But it may be that we get to the point where we need an existing
    // user in the container.
    TEST_IMAGE.inside("--ulimit nofile=1024:1024 --init") {
        stage('test python3 unit') {
            dir ('tests') {
                ansiColor('css') {
                    sh "bash -c \"make test-unit-shell\"";
                }
            }
        }
    }
    */
}
return this;

