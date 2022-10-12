#!groovy

// library for uploading packages
package lib

def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

def download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}_0.${DISTRO}_amd64.deb"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, DISTRO)
}

def download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}.*.tar.gz"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'source tar')
}

def download_docker_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    def FILE_PATTERN = versioning.get_docker_artifact_name(EDITION, CMK_VERSION)
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'docker tar')
}

def download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, PATTERN = "*", INFO = 'all packages') {
    println("""
        ||== download_version_dir() ================================================================
        || DOWNLOAD_SOURCE = |${DOWNLOAD_SOURCE}|
        || PORT =            |${PORT}|
        || CMK_VERSION =     |${CMK_VERSION}|
        || DOWNLOAD_DEST =   |${DOWNLOAD_DEST}|
        || PATTERN =         |${PATTERN}|
        || INFO =            |${INFO}|
        ||==========================================================================================
        """.stripMargin());
    stage("Download from shared storage (${INFO})") {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh("mkdir -p ${DOWNLOAD_DEST}")
            sh """
                rsync --recursive --links --perms --times --verbose \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    ${DOWNLOAD_SOURCE}/${CMK_VERSION}/${PATTERN} \
                    ${DOWNLOAD_DEST}/
            """
        }
    }
}

def upload_version_dir(SOURCE_PATH, UPLOAD_DEST, PORT) {
    stage('Upload to download server') {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                rsync -av \
                    -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                    ${SOURCE_PATH} \
                    ${UPLOAD_DEST}
            """
        }
    }
}

def upload_via_rsync(archive_base, cmk_version, filename, upload_dest, upload_port) {
    println("""
        ||== upload_via_rsync() ================================================
        || archive_base = |${archive_base}|
        || cmk_version =  |${cmk_version}|
        || filename =     |${filename}|
        || upload_dest =  |${upload_dest}|
        || upload_port =  |${upload_port}|
        ||======================================================================
        """.stripMargin());

    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh("""
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no \
                -i ${RELEASE_KEY} -p ${upload_port}" \
                ${archive_base}/./${cmk_version}/${filename} \
                ${upload_dest}
        """);
    }
}

def create_hashes(ARCHIVE_DIR) {
    stage("Create file hashes") {
        def HASHES_PATH = ARCHIVE_DIR + "/HASHES"
        sh("cd ${ARCHIVE_DIR} ; sha256sum -- *.{tar.gz,rpm,deb,cma,cmk} | sort -k 2 > ${HASHES_PATH}")
    }
}

def deploy_to_website(UPLOAD_URL, PORT, CMK_VERS) {
    stage("Deploy to Website") {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh("""
                ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT} ${UPLOAD_URL} \
                    ln -sf /var/downloads/checkmk/${CMK_VERS} /smb-share-customer/checkmk
            """);
        }
    }
}

return this
