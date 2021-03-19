// library for simple string modifications
package lib

// Strip the protocol from an URL
// For example, the docker registry is sometimes needed with and without protocol
def strip_protocol_from_url (URL) {
    def URL_STRIPPED = URL.split('://')[1]
    return URL_STRIPPED
}

return this
