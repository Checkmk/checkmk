#!groovy

/// file: test-python3-unit-all.groovy

def main() {
    inside_container(
        init: true,
        ulimit_nofile: 1024,
    ) {
        stage('run test-unit-all') {
            dir("${checkout_dir}") {
                withCredentials([
                ]) {
                    withCredentialFileAtLocation(credentialsId:"remote.bazelrc", location:"${checkout_dir}/remote.bazelrc") {
                        lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource: null) {
                            sh("make -C tests test-unit-all");
                        }
                    }
                }
            }
        }
    }
}

return this;
