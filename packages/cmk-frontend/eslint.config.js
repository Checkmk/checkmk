module.exports = {
    ignores: [
        // These are just copied files and should be replaced with npm
        // dependencies in the future
        "src/js/modules/cbor_ext.*s",
        "src/js/modules/colorpicker.*s",

        // These are generated files or included libraries
        "src/js/mobile_min.js",
        "src/js/side_min.js",
        "src/jquery/jquery.mobile-1.4.5.js",
        "src/jquery/jquery.mobile-1.4.5.min.js",
        "src/js/main_min.js",

        "src/openapi/swagger-ui-3/swagger-ui-bundle.js",
        "src/openapi/swagger-ui-3/swagger-ui-es-bundle.js",
        "src/openapi/swagger-ui-3/swagger-ui.js",
        "src/openapi/swagger-ui-3/swagger-ui-standalone-preset.js",
        "src/openapi/swagger-ui-3/swagger-ui-es-bundle-core.js",
        "src/openapi/redoc.standalone.js",
    ],
};
