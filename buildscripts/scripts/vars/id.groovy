def getUser(USER_NAME) {
    return sh(script: "id -u ${USER_NAME}", returnStdout: true).trim()
}
def getGroup(GROUP_NAME) {
    return sh(script: "id -u ${GROUP_NAME}", returnStdout: true).trim()
}
def setOwner(USER_ID, GROUP_ID, PATH) {
    sh(script: "chown -R ${USER_ID}:${GROUP_ID} ${PATH}")
}
