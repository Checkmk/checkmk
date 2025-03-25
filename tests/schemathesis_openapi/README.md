Schemathesis tests
==================

The Schemathesis tests are validating the functionality of the Checkmk
REST API. The default behaviour of the tests can be modified by some
environment variables described below.

# Environment variables

* SCHEMATHESIS_SCHEMA_DIR ... OpenAPI schema directory to use instead of schema URL (default: None)
* SCHEMATHESIS_ALLOW_NULLS .. Allow NULL bytes in sample data generation (default: False)
* SCHEMATHESIS_CODEC ........ Specify the codec for the sample data generation (default: "utf-8")
* SCHEMATHESIS_SUPPRESS ..... Comma-separated list of suppressed known-issues (default: <all>)
* SCHEMATHESIS_ALLOW ........ Comma-separated list of unsuppressed known-issues (default: None)
* SCHEMATHESIS_METHOD ....... The method to use for the stateless testing (default: <all>)
* SCHEMATHESIS_ENDPOINT ..... The endpoint to use for the stateless testing (default: <all>)
* SCHMATHESIS_PROFILE ....... The configuration profile to use for the testing (default: "default")
                              Available options: "default", "qa", "ci", "debug"