// library for uploading packages
package lib

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where should the packages be uploaded to
    // PORT: Port fo upload dest
    stage(args.NAME + ' upload package') {
        def FILE_BASE = get_file_base(args.FILE_PATH)
        def ARCHIVE_BASE = get_archive_base(FILE_BASE)
        
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST, args.PORT)
    }
}

def download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}_0.${DISTRO}_amd64.deb"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, DISTRO)
}

def download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}.*.tar.gz"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'source tar')
}

def download_docker_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION) {
    def FILE_PATTERN = "check-mk-${EDITION}-docker-${CMK_VERSION}.tar.gz"
    download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN, 'docker tar')
}

def download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, PATTERN = "*", INFO = 'all packages') {
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

def upload_version_dir(SOURCE_PATH, UPLOAD_DEST, PORT)
{
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

def get_file_base(FILE_PATH) {
    return sh(script: "dirname ${FILE_PATH}", returnStdout: true).toString().trim()
}

def get_archive_base(FILE_BASE) {
    return sh(script: "dirname ${FILE_BASE}", returnStdout: true).toString().trim()
}

def get_file_name(FILE_PATH) {
    return sh(script: "basename ${FILE_PATH}", returnStdout: true).toString().trim()
}

def via_rsync(ARCHIVE_BASE, CMK_VERS, FILE_NAME, UPLOAD_DEST, PORT) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                ${ARCHIVE_BASE}/./${CMK_VERS}/${FILE_NAME} \
                ${UPLOAD_DEST}
        """
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
            sh """
                ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT} ${UPLOAD_URL} \
                    ln -sf /var/downloads/checkmk/${CMK_VERS} /smb-share-customer/checkmk
            """
        }
    }
}

return this
