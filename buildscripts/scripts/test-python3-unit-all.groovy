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
                    usernamePassword(
                        credentialsId: 'bazel-caching-credentials',
                        /// BAZEL_CACHE_URL must be set already, e.g. via Jenkins config
                        passwordVariable: 'BAZEL_CACHE_PASSWORD',
                        usernameVariable: 'BAZEL_CACHE_USER'),
                ]) {
                    lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
                        sh("make -C tests test-unit-all");
                    }
                }
            }
        }
    }
}

return this;
