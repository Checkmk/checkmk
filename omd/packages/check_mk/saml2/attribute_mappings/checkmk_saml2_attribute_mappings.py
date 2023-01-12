# This is a pysaml2 specific workaround.
#
# pysaml2 maps the attribute names to what it deems friendly names using the mapping defined in their [default attribute mappings](
# https://github.com/IdentityPython/pysaml2/tree/master/src/saml2/attributemaps).
#
# This is **against** the [SAML specification](http://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf).
# Attribute names are the source of truth to make authentication and authorisation decisions and must not be modified.
#
# SAML provides a way to configure user-friendly names.
# These are optional and appear in the `FriendlyName` field.
#
# Additionally, the mapping approach is confusing for everyone.
# What the customer sees and knows are the actual attribute names.
# From there, they would need to look up what each attribute is mapped to using pysaml2 source code.
#
# The purpose of the file here is to override the default mapping provided by pysaml2.
# It contains no elements, so that all attribute names remain unchanged.
#
# TODO:
# - This could be removed once the maintainer finds a consensus: <https://github.com/IdentityPython/pysaml2/issues/549>

MAP = {
    "identifier": "",
    "fro": {},
    "to": {},
}
