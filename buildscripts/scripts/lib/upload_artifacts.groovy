// library for uploading packages
package lib

hashfile_extension = ".hash"

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where should the packages be uploaded to
    // PORT: Port fo upload dest
    def FILE_BASE = get_file_base(args.FILE_PATH)
    def ARCHIVE_BASE = get_archive_base(FILE_BASE)

    create_hash(args.FILE_PATH)

    stage(args.FILE_NAME + ' upload package and hash file') {
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST, args.PORT)
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME + hashfile_extension, args.UPLOAD_DEST, args.PORT)
    }
}

def download_deb(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    stage(DISTRO + ' download package') {
        def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}_0.${DISTRO}_amd64.deb"
        download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN)
    }
}

def download_source_tar(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, EDITION, DISTRO) {
    stage(DISTRO + ' download package') {
        def FILE_PATTERN = "check-mk-${EDITION}-${CMK_VERSION}.*.tar.gz"
        download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, FILE_PATTERN)
    }
}

def download_version_dir(DOWNLOAD_SOURCE, PORT, CMK_VERSION, DOWNLOAD_DEST, PATTERN = "*") {
    stage('Download from shared storage') {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                rsync -av \
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

def create_hash(FILE_PATH) {
    stage("Create file hash") {
        sh("""
            cd \$(dirname ${FILE_PATH});
            sha256sum -- \$(basename ${FILE_PATH}) > "\$(basename ${FILE_PATH})${hashfile_extension}";
        """);
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
