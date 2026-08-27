/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalSettingsApp } from 'cmk-shared-typing/typescript/global_settings'

export const globalSettingsPagePayload = {
  title: 'Global settings',
  domain: 'global_settings',
  scope: {
    type: 'global'
  },
  topics: [
    {
      icon: 'configuration',
      headline: 'Site management',
      subline: 'Settings that control the behavior of this site',
      warning: null,
      variables: [
        {
          name: 'inventory_cleanup',
          spec: {
            title: 'HW/SW inventory cleanup',
            help: '',
            validators: [],
            groups: [],
            no_elements_text: '(no parameters)',
            additional_static_elements: {},
            elements: [
              {
                name: 'for_hosts',
                required: true,
                group: null,
                default_value: [],
                render_only: false,
                parameter_form: {
                  title: 'For specific hosts',
                  help: '',
                  validators: [],
                  element_template: {
                    title: '',
                    help: '',
                    validators: [],
                    groups: [],
                    no_elements_text: '(no parameters)',
                    additional_static_elements: {},
                    elements: [
                      {
                        name: 'regex_or_explicit',
                        required: true,
                        group: null,
                        default_value: [],
                        render_only: false,
                        parameter_form: {
                          title: 'Match host names',
                          help: '',
                          validators: [
                            {
                              min_value: 1,
                              max_value: null,
                              error_message: 'The minimum allowed length is 1.',
                              type: 'length_in_range'
                            }
                          ],
                          element_template: {
                            title: '',
                            help: '',
                            validators: [],
                            no_elements_text: '(No choices available)',
                            label: null,
                            input_hint: null,
                            type: 'cascading_single_choice',
                            elements: [
                              {
                                name: 'alternative_explicit',
                                title: 'Explicit match',
                                default_value: '',
                                parameter_form: {
                                  title: 'Explicit match',
                                  help: '',
                                  validators: [],
                                  label: null,
                                  input_hint: '',
                                  field_size: 'medium',
                                  autocompleter: null,
                                  type: 'string'
                                }
                              },
                              {
                                name: 'alternative_regex',
                                title: 'Regular expression match',
                                default_value: '',
                                parameter_form: {
                                  title: 'Regular expression match',
                                  help: 'The match is case sensitive. The text entered here is handled as a regular expression pattern. The pattern is matched from the beginning. Add a tailing <tt>$</tt> to change it to a whole text match. Read more about <a href="https://docs.checkmk.com/3.0.0/en/regexes.html?utm_campaign=inline_help&utm_content=unknown.htmllib.html&utm_medium=app&utm_source=checkmk&utm_term=3.0.0b1_community" target="_blank">regular expression matching in Checkmk</a> in our User Guide.',
                                  validators: [],
                                  label: null,
                                  input_hint: '',
                                  field_size: 'medium',
                                  autocompleter: null,
                                  type: 'string'
                                }
                              }
                            ],
                            layout: 'vertical'
                          },
                          element_default_value: ['alternative_explicit', ''],
                          editable_order: true,
                          add_element_label: 'Add new entry',
                          remove_element_label: 'Remove this entry',
                          no_element_label: 'No entries',
                          type: 'list'
                        }
                      },
                      {
                        name: 'parameters',
                        required: true,
                        group: null,
                        default_value: ['file_age', 34560000.0],
                        render_only: false,
                        parameter_form: {
                          title: 'Cleanup parameters',
                          help: '',
                          validators: [],
                          no_elements_text: '(No choices available)',
                          label: null,
                          input_hint: null,
                          type: 'cascading_single_choice',
                          elements: [
                            {
                              name: 'file_age',
                              title: 'Remove history entries older than',
                              default_value: 34560000.0,
                              parameter_form: {
                                title: 'Remove history entries older than',
                                help: '',
                                validators: [
                                  {
                                    error_message: 'Number is not a float value.',
                                    type: 'is_float'
                                  },
                                  {
                                    min_value: 1,
                                    max_value: null,
                                    error_message: 'The minimum allowed value is 1.',
                                    type: 'number_in_range'
                                  }
                                ],
                                label: '',
                                i18n: {
                                  millisecond: 'ms',
                                  second: 's',
                                  minute: 'min',
                                  hour: 'h',
                                  day: 'd',
                                  validation_negative_number: 'Negative values not allowed'
                                },
                                displayed_magnitudes: ['day'],
                                input_hint: null,
                                type: 'time_span'
                              }
                            },
                            {
                              name: 'number_of_history_entries',
                              title: 'Remove history entries right after',
                              default_value: 100,
                              parameter_form: {
                                title: 'Remove history entries right after',
                                help: '',
                                validators: [
                                  {
                                    error_message: 'Number is not an integer value.',
                                    type: 'is_integer'
                                  },
                                  {
                                    min_value: 1,
                                    max_value: null,
                                    error_message: 'The minimum allowed value is 1.',
                                    type: 'number_in_range'
                                  }
                                ],
                                label: 'entry number',
                                unit: '',
                                input_hint: null,
                                type: 'integer'
                              }
                            },
                            {
                              name: 'combined',
                              title: 'Remove history entries which meet the following conditions',
                              default_value: {
                                strategy:
                                  '8ee6aa32341bb939c07d80529df3febfb4f1398244d1c37f7d6f8476a6316605',
                                file_age: 34560000.0,
                                number_of_history_entries: 100
                              },
                              parameter_form: {
                                title: 'Use the following defaults',
                                help: '',
                                validators: [],
                                groups: [],
                                no_elements_text: '(no parameters)',
                                additional_static_elements: {},
                                elements: [
                                  {
                                    name: 'strategy',
                                    required: true,
                                    group: null,
                                    default_value:
                                      '8ee6aa32341bb939c07d80529df3febfb4f1398244d1c37f7d6f8476a6316605',
                                    render_only: false,
                                    parameter_form: {
                                      title: 'Cleanup strategy',
                                      help: '',
                                      validators: [],
                                      no_elements_text: '',
                                      frozen: false,
                                      label: '',
                                      input_hint: 'Please choose',
                                      type: 'single_choice',
                                      elements: [
                                        {
                                          name: '8ee6aa32341bb939c07d80529df3febfb4f1398244d1c37f7d6f8476a6316605',
                                          title: 'Both conditions must match (defensive)'
                                        },
                                        {
                                          name: '0f5962d7e4c6d8ed93b2636830bfae72004d29f0e6aa90e45388fc6999fa82f9',
                                          title: 'One condition needs to match (offensive)'
                                        }
                                      ]
                                    }
                                  },
                                  {
                                    name: 'file_age',
                                    required: true,
                                    group: null,
                                    default_value: 34560000.0,
                                    render_only: false,
                                    parameter_form: {
                                      title: 'Remove history entries older than',
                                      help: '',
                                      validators: [
                                        {
                                          error_message: 'Number is not a float value.',
                                          type: 'is_float'
                                        },
                                        {
                                          min_value: 1,
                                          max_value: null,
                                          error_message: 'The minimum allowed value is 1.',
                                          type: 'number_in_range'
                                        }
                                      ],
                                      label: '',
                                      i18n: {
                                        millisecond: 'ms',
                                        second: 's',
                                        minute: 'min',
                                        hour: 'h',
                                        day: 'd',
                                        validation_negative_number: 'Negative values not allowed'
                                      },
                                      displayed_magnitudes: ['day'],
                                      input_hint: null,
                                      type: 'time_span'
                                    }
                                  },
                                  {
                                    name: 'number_of_history_entries',
                                    required: true,
                                    group: null,
                                    default_value: 100,
                                    render_only: false,
                                    parameter_form: {
                                      title: 'Remove history entries right after',
                                      help: '',
                                      validators: [
                                        {
                                          error_message: 'Number is not an integer value.',
                                          type: 'is_integer'
                                        },
                                        {
                                          min_value: 1,
                                          max_value: null,
                                          error_message: 'The minimum allowed value is 1.',
                                          type: 'number_in_range'
                                        }
                                      ],
                                      label: 'entry number',
                                      unit: '',
                                      input_hint: null,
                                      type: 'integer'
                                    }
                                  }
                                ],
                                type: 'dictionary'
                              }
                            }
                          ],
                          layout: 'vertical'
                        }
                      }
                    ],
                    type: 'dictionary'
                  },
                  element_default_value: {
                    regex_or_explicit: [],
                    parameters: ['file_age', 34560000.0]
                  },
                  editable_order: true,
                  add_element_label: 'Add new entry',
                  remove_element_label: 'Remove this entry',
                  no_element_label: 'No entries',
                  type: 'list'
                }
              },
              {
                name: 'default',
                required: true,
                group: null,
                default_value: ['alternative_no_defaults', null],
                render_only: false,
                parameter_form: {
                  title: 'Default cleanup parameters',
                  help: '',
                  validators: [],
                  no_elements_text: '(No choices available)',
                  label: null,
                  input_hint: null,
                  type: 'cascading_single_choice',
                  elements: [
                    {
                      name: 'alternative_defaults',
                      title: 'Use the following defaults',
                      default_value: {
                        strategy: 'and',
                        file_age: 34560000.0,
                        number_of_history_entries: 100
                      },
                      parameter_form: {
                        title: 'Use the following defaults',
                        help: '',
                        validators: [],
                        groups: [],
                        no_elements_text: '(no parameters)',
                        additional_static_elements: {},
                        elements: [
                          {
                            name: 'strategy',
                            required: true,
                            group: null,
                            default_value: 'and',
                            render_only: false,
                            parameter_form: {
                              title: 'Cleanup strategy',
                              help: '',
                              validators: [],
                              label: 'Both conditions must match (defensive)',
                              value: 'and',
                              type: 'fixed_value'
                            }
                          },
                          {
                            name: 'file_age',
                            required: true,
                            group: null,
                            default_value: 34560000.0,
                            render_only: false,
                            parameter_form: {
                              title: 'Remove history entries older than',
                              help: '',
                              validators: [
                                {
                                  error_message: 'Number is not a float value.',
                                  type: 'is_float'
                                },
                                {
                                  min_value: 1,
                                  max_value: null,
                                  error_message: 'The minimum allowed value is 1.',
                                  type: 'number_in_range'
                                }
                              ],
                              label: '',
                              i18n: {
                                millisecond: 'ms',
                                second: 's',
                                minute: 'min',
                                hour: 'h',
                                day: 'd',
                                validation_negative_number: 'Negative values not allowed'
                              },
                              displayed_magnitudes: ['day'],
                              input_hint: null,
                              type: 'time_span'
                            }
                          },
                          {
                            name: 'number_of_history_entries',
                            required: true,
                            group: null,
                            default_value: 100,
                            render_only: false,
                            parameter_form: {
                              title: 'Remove history entries right after',
                              help: '',
                              validators: [
                                {
                                  error_message: 'Number is not an integer value.',
                                  type: 'is_integer'
                                },
                                {
                                  min_value: 1,
                                  max_value: null,
                                  error_message: 'The minimum allowed value is 1.',
                                  type: 'number_in_range'
                                }
                              ],
                              label: 'entry number',
                              unit: '',
                              input_hint: null,
                              type: 'integer'
                            }
                          }
                        ],
                        type: 'dictionary'
                      }
                    },
                    {
                      name: 'alternative_no_defaults',
                      title: 'No defaults',
                      default_value: null,
                      parameter_form: {
                        title: '',
                        help: '',
                        validators: [],
                        label: null,
                        value: null,
                        type: 'fixed_value'
                      }
                    }
                  ],
                  layout: 'vertical'
                }
              },
              {
                name: 'abandoned_file_age',
                required: true,
                group: null,
                default_value: 2592000.0,
                render_only: false,
                parameter_form: {
                  title: 'Remove abandoned host files older than',
                  help: '',
                  validators: [
                    {
                      error_message: 'Number is not a float value.',
                      type: 'is_float'
                    },
                    {
                      min_value: 1,
                      max_value: null,
                      error_message: 'The minimum allowed value is 1.',
                      type: 'number_in_range'
                    }
                  ],
                  label: '',
                  i18n: {
                    millisecond: 'ms',
                    second: 's',
                    minute: 'min',
                    hour: 'h',
                    day: 'd',
                    validation_negative_number: 'Negative values not allowed'
                  },
                  displayed_magnitudes: ['day'],
                  input_hint: null,
                  type: 'time_span'
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            for_hosts: [],
            default: ['alternative_no_defaults', null],
            abandoned_file_age: 2592000.0
          },
          default_value: {
            for_hosts: [],
            default: ['alternative_no_defaults', null],
            abandoned_file_age: 2592000.0
          },
          modified: false,
          site_overrides: []
        },
        {
          name: 'trusted_certificate_authorities',
          spec: {
            title: 'Trusted certificate authorities for SSL',
            help: 'Whenever a server component of Checkmk opens an SSL connection, it uses the certificate authorities configured here for verifying the SSL certificate of the destination server. This is used for example when performing Setup replication to remote sites or when special agents are communicating via HTTPS. The CA certificates configured here will be written to the CA bundle /tmp/pytest_cmk_5ueyhyml/var/ssl/ca-certificates.crt.',
            validators: [],
            groups: [],
            no_elements_text: '(no parameters)',
            additional_static_elements: {},
            elements: [
              {
                name: 'use_system_wide_cas',
                required: true,
                group: null,
                default_value: true,
                render_only: false,
                parameter_form: {
                  title: 'Use system wide CAs',
                  help: 'All supported Linux distributions provide a mechanism of managing trusted CAs. Depending on your Linux distributions the paths where these CAs are stored and the commands to manage the CAs differ. Please check out the documentation of your Linux distribution in case you want to customize trusted CAs system wide. You can choose here to trust the system wide CAs here. Checkmk will search these directories for system wide CAs: /etc/ssl/certs, /etc/pki/tls/certs',
                  validators: [],
                  label: 'Trust system wide configured CAs',
                  text_on: 'on',
                  text_off: 'off',
                  type: 'boolean_choice'
                }
              },
              {
                name: 'trusted_cas',
                required: true,
                group: null,
                default_value: [],
                render_only: false,
                parameter_form: {
                  title: 'Manually added',
                  help: 'Only accepting HTTPS connections with a server which certificate is signed with one of the CAs that are listed here. That way it is guaranteed that it is communicating only with the authentic server. If you use self signed certificates for you server then enter that certificate here.',
                  validators: [],
                  element_template: {
                    title: 'Certificate chain (root / intermediate certificate)',
                    help: '',
                    validators: [],
                    label: null,
                    input_hint: '',
                    allow_fetch: true,
                    type: 'ca_certificate'
                  },
                  element_default_value: '',
                  editable_order: false,
                  add_element_label: 'Add new CA certificate or chain',
                  remove_element_label: 'Remove this entry',
                  no_element_label: 'No entries',
                  type: 'list'
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            use_system_wide_cas: true,
            trusted_cas: []
          },
          default_value: {
            use_system_wide_cas: true,
            trusted_cas: []
          },
          modified: false,
          site_overrides: [
            {
              site_id: 'muc',
              title: 'Munich site',
              url: 'wato.py?mode=edit_site_globals&site=muc'
            },
            {
              site_id: 'ber',
              title: 'Berlin site',
              url: 'wato.py?mode=edit_site_globals&site=ber'
            }
          ]
        },
        {
          name: 'site_subject_alternative_names',
          spec: {
            title: 'Site certificate subject alternative names',
            help: 'Set the host names or IP addresses of the site. The entries will be added as additional subject alternative names (SANs) to the site certificate, alongside the default SANs. Configuring this allows proper server name identification when connecting to the site via TLS, for example for instrumented applications connecting to the OpenTelemetry collector.\\nNote: Changing this setting will trigger re-issuance of the site certificate by the site CA. In distributed setups, configure SANs separately for each site in the distributed monitoring configuration.',
            validators: [],
            element_template: {
              title: '',
              help: '',
              validators: [],
              label: null,
              input_hint: '',
              field_size: 'medium',
              autocompleter: null,
              type: 'string'
            },
            element_default_value: '',
            editable_order: true,
            add_element_label: 'Add new entry',
            remove_element_label: 'Remove this entry',
            no_element_label: 'No entries',
            type: 'list'
          },
          value: [],
          default_value: [],
          modified: false,
          site_overrides: []
        },
        {
          name: 'agent_controller_certificates',
          spec: {
            title: 'Agent certificates',
            help: 'Settings for certificates issued to registered agents.',
            validators: [],
            groups: [],
            no_elements_text: '(no parameters)',
            additional_static_elements: {},
            elements: [
              {
                name: 'lifetime_in_months',
                required: true,
                group: null,
                default_value: '39fa9ec190eee7b6f4dff1100d6343e10918d044c75eac8f9e9a2596173f80c9',
                render_only: false,
                parameter_form: {
                  title: 'Lifetime of certificates',
                  help: 'This setting limits the validity of agent certificates. Active agents (i.e., the Agent Controller is running as a daemon) will automatically call the Checkmk site for renewal when certificates are about to expire. Hence, with this setting, you can assure that registrations of inactive agents expire after a given time.',
                  validators: [],
                  no_elements_text: '',
                  frozen: false,
                  label: '',
                  input_hint: 'Please choose',
                  type: 'single_choice',
                  elements: [
                    {
                      name: '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce',
                      title: '3 months'
                    },
                    {
                      name: 'e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683',
                      title: '6 months'
                    },
                    {
                      name: '6b51d431df5d7f141cbececcf79edf3dd861c3b4069f0b11661a3eefacbba918',
                      title: '1 year'
                    },
                    {
                      name: 'c2356069e9d1e79ca924378153cfbbfb4d4416b1f99d41a2940bfdb66c5319db',
                      title: '2 years'
                    },
                    {
                      name: '39fa9ec190eee7b6f4dff1100d6343e10918d044c75eac8f9e9a2596173f80c9',
                      title: '5 years'
                    },
                    {
                      name: '2abaca4911e68fa9bfbf3482ee797fd5b9045b841fdff7253557c5fe15de6477',
                      title: '10 years'
                    },
                    {
                      name: '284b7e6d788f363f910f7beb1910473e23ce9d6c871f1ce0f31f22a982d48ad4',
                      title: '50 years'
                    }
                  ]
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            lifetime_in_months: '39fa9ec190eee7b6f4dff1100d6343e10918d044c75eac8f9e9a2596173f80c9'
          },
          default_value: {
            lifetime_in_months: '39fa9ec190eee7b6f4dff1100d6343e10918d044c75eac8f9e9a2596173f80c9'
          },
          modified: false,
          site_overrides: []
        },
        {
          name: 'rest_api_etag_locking',
          spec: {
            title: 'REST API: Use HTTP ETags for optimistic locking',
            help: 'When multiple HTTP clients want to update an object at the same time, it can happen that the slower client will overwrite changes by the faster one. This is commonly referred to as the &#x27;lost update problem&#x27;. To prevent this situation from happening, the REST API of Checkmk does &#x27;optimistic locking&#x27; using HTTP ETag headers. In this case the Object&#x27;s ETag has to be sent to the server with a HTTP If-Match header. This behavior can be deactivated, but this will allow the &#x27;lost update problem&#x27; to occur.',
            validators: [],
            label: '',
            text_on: 'on',
            text_off: 'off',
            type: 'boolean_choice'
          },
          value: true,
          default_value: true,
          modified: false,
          site_overrides: []
        },
        {
          name: 'site_autostart',
          spec: {
            title: 'Start during system boot',
            help: 'Whether or not this site should be started during startup of the Checkmk server.',
            validators: [],
            label: '',
            text_on: 'on',
            text_off: 'off',
            type: 'boolean_choice'
          },
          value: false,
          default_value: false,
          modified: false,
          site_overrides: []
        },
        {
          name: 'site_core',
          spec: {
            title: 'Monitoring core',
            help: 'Choose the monitoring core to run for monitoring. You can also decide to run no monitoring core in this site. This can be useful for instances running only a GUI for connecting to other monitoring sites.',
            validators: [],
            no_elements_text: '',
            frozen: false,
            label: '',
            input_hint: 'Please choose',
            type: 'single_choice',
            elements: [
              {
                name: '70f7aeeb316d7dfa4aade066d9b7f62dcd88ef58c669372ba42a10aa9dcbc85c',
                title: 'Nagios 3'
              },
              {
                name: '5dc808cc885eaa96b1822f3f61ed3c4205bc29915cb99ddb1896aa6bed29f414',
                title: 'No monitoring core'
              }
            ]
          },
          value: null,
          default_value: null,
          modified: false,
          site_overrides: []
        },
        {
          name: 'site_livestatus_tcp',
          spec: {
            title: 'Access to Livestatus via TCP',
            help: 'Check_MK Livestatus usually listens only on a local Unix socket - for reasons of performance and security. This option is used to make it reachable via TCP on a port configurable with LIVESTATUS_TCP_PORT.',
            validators: [],
            parameter_form: {
              title: '',
              help: '',
              validators: [],
              groups: [],
              no_elements_text: '(no parameters)',
              additional_static_elements: {},
              elements: [
                {
                  name: 'port',
                  required: true,
                  group: null,
                  default_value: 6557,
                  render_only: false,
                  parameter_form: {
                    title: 'TCP port',
                    help: '',
                    validators: [
                      {
                        error_message: 'Number is not an integer value.',
                        type: 'is_integer'
                      },
                      {
                        min_value: 1,
                        max_value: 65535,
                        error_message: 'Allowed values range from 1 to 65535.',
                        type: 'number_in_range'
                      }
                    ],
                    label: '',
                    unit: '',
                    input_hint: null,
                    type: 'integer'
                  }
                },
                {
                  name: 'only_from',
                  required: true,
                  group: null,
                  default_value: ['0.0.0.0', '::/0'],
                  render_only: false,
                  parameter_form: {
                    title: 'Restrict access to IP addresses',
                    help: 'The access to Livestatus via TCP will only be allowed from the configured source IP addresses. You can either configure specific IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>.',
                    validators: [
                      {
                        min_value: 1,
                        max_value: null,
                        error_message: 'The minimum allowed length is 1.',
                        type: 'length_in_range'
                      }
                    ],
                    string_spec: {
                      title: '',
                      help: '',
                      validators: [],
                      label: null,
                      input_hint: '',
                      field_size: 'medium',
                      autocompleter: null,
                      type: 'string'
                    },
                    type: 'list_of_strings',
                    string_default_value: '',
                    layout: 'horizontal'
                  }
                },
                {
                  name: 'instances',
                  required: true,
                  group: null,
                  default_value: 500,
                  render_only: false,
                  parameter_form: {
                    title: 'Maximum number of parallel server instances',
                    help: 'Limits the number of Livestatus server processes that can be active simultaneously.',
                    validators: [
                      {
                        error_message: 'Number is not an integer value.',
                        type: 'is_integer'
                      }
                    ],
                    label: '',
                    unit: '',
                    input_hint: null,
                    type: 'integer'
                  }
                },
                {
                  name: 'per_source',
                  required: true,
                  group: null,
                  default_value: 250,
                  render_only: false,
                  parameter_form: {
                    title: 'Maximum parallel connections per source IP address',
                    help: 'Limits the number of simultaneous Livestatus connections allowed from a single source IP address.',
                    validators: [
                      {
                        error_message: 'Number is not an integer value.',
                        type: 'is_integer'
                      }
                    ],
                    label: '',
                    unit: '',
                    input_hint: null,
                    type: 'integer'
                  }
                },
                {
                  name: 'tls',
                  required: false,
                  group: null,
                  default_value: true,
                  render_only: false,
                  parameter_form: {
                    title: 'Encrypt communication',
                    help: 'Since Checkmk 1.6 it is possible to encrypt the TCP Livestatus connections using SSL. This is enabled by default for sites that enable Livestatus via TCP with 1.6 or newer. Sites that already have this option enabled keep the communication unencrypted for compatibility reasons. However, it is highly recommended to migrate to an encrypted communication.',
                    validators: [],
                    label: 'Encrypt TCP Livestatus connections',
                    value: true,
                    type: 'fixed_value'
                  }
                }
              ],
              type: 'dictionary'
            },
            i18n: {
              label: 'Enable Livestatus access via network (TCP)',
              none_label: 'Livestatus is available locally'
            },
            parameter_form_default_value: {
              port: 6557,
              only_from: ['0.0.0.0', '::/0'],
              instances: 500,
              per_source: 250
            },
            type: 'optional_choice'
          },
          value: null,
          default_value: null,
          modified: false,
          site_overrides: []
        },
        {
          name: 'diskspace_cleanup',
          spec: {
            title: 'Automatic disk space cleanup',
            help: 'You can configure your monitoring site to free disk space based on the ages of files or free space of the volume the site is placed on.<br>The monitoring site is executing the program <tt>diskspace</tt> 5 minutes past every full hour as a cronjob. Details about the execution are logged to the file <tt>var/log/diskspace.log</tt>. You can always execute this program manually (add the <tt>-v</tt> option to see details about the actions taken).',
            validators: [],
            groups: [],
            no_elements_text: 'Disk space cleanup is disabled',
            additional_static_elements: {},
            elements: [
              {
                name: 'max_file_age',
                required: false,
                group: null,
                default_value: 31536000.0,
                render_only: false,
                parameter_form: {
                  title: 'Delete files older than',
                  help: 'The historic events (state changes, downtimes etc.) of your hosts and services are stored in the monitoring history as plain text log files. One history log file contains the monitoring history of a given time period of all hosts and services. The files which are older than the configured time will be removed on the next execution of the disk space cleanup.<br>The historic metrics are stored in files for each host and service individually. When a host or service has been removed from the monitoring, its metric files remain untouched on your disk until the files last update (modification time) is longer ago than the configured age.',
                  validators: [
                    {
                      error_message: 'Number is not a float value.',
                      type: 'is_float'
                    },
                    {
                      min_value: 1,
                      max_value: null,
                      error_message: 'The minimum allowed value is 1.',
                      type: 'number_in_range'
                    }
                  ],
                  label: '',
                  i18n: {
                    millisecond: 'ms',
                    second: 's',
                    minute: 'min',
                    hour: 'h',
                    day: 'd',
                    validation_negative_number: 'Negative values not allowed'
                  },
                  displayed_magnitudes: ['day', 'hour', 'minute', 'second'],
                  input_hint: null,
                  type: 'time_span'
                }
              },
              {
                name: 'min_free_bytes',
                required: false,
                group: null,
                default_value: [['', 'B'], 2592000.0],
                render_only: false,
                parameter_form: {
                  title: 'Delete additional files when disk space is below',
                  help: 'When the disk space cleanup by file age was not able to gain enough free disk space, then the cleanup mechanism starts cleaning up additional files. The files are deleted by age, the oldest first, until the files are newer than the configured minimum file age.',
                  validators: [],
                  elements: [
                    {
                      title: 'Clean up when disk space is below',
                      help: '',
                      validators: [
                        {
                          error_message: 'Number is not a float value.',
                          type: 'is_float'
                        },
                        {
                          min_value: 1,
                          max_value: null,
                          error_message: 'The minimum allowed value is 1.',
                          type: 'number_in_range'
                        }
                      ],
                      label: '',
                      displayed_magnitudes: ['B', 'KiB', 'MiB', 'GiB', 'TiB'],
                      input_hint: '0',
                      i18n: {
                        choose_unit: 'Choose unit'
                      },
                      type: 'data_size'
                    },
                    {
                      title: 'Never remove files newer than',
                      help: 'With this option you can prevent cleanup of files which have been updated within this time range.',
                      validators: [
                        {
                          error_message: 'Number is not a float value.',
                          type: 'is_float'
                        },
                        {
                          min_value: 1,
                          max_value: null,
                          error_message: 'The minimum allowed value is 1.',
                          type: 'number_in_range'
                        }
                      ],
                      label: '',
                      i18n: {
                        millisecond: 'ms',
                        second: 's',
                        minute: 'min',
                        hour: 'h',
                        day: 'd',
                        validation_negative_number: 'Negative values not allowed'
                      },
                      displayed_magnitudes: ['day', 'hour', 'minute', 'second'],
                      input_hint: null,
                      type: 'time_span'
                    }
                  ],
                  show_titles: true,
                  type: 'tuple',
                  layout: 'vertical'
                }
              },
              {
                name: 'cleanup_abandoned_host_files',
                required: false,
                group: null,
                default_value: 2592000.0,
                render_only: false,
                parameter_form: {
                  title: 'Clean up abandoned host files older than',
                  help: 'During monitoring there are several dedicated files created for each host. There are, for example, the discovered services, performance data and different temporary files created. During deletion of a host, these files are normally deleted. But there are cases, where the files are left on the disk until manual deletion, for example if you move a host from one site to another or deleting a host manually from the configuration.<br>The performance data (RRDs) and HW/SW Inventory archive are never deleted during host deletion. They are only deleted automatically when you enable this option and after the configured period.',
                  validators: [
                    {
                      error_message: 'Number is not a float value.',
                      type: 'is_float'
                    },
                    {
                      min_value: 3600,
                      max_value: null,
                      error_message: 'The minimum allowed value is 3600.',
                      type: 'number_in_range'
                    }
                  ],
                  label: '',
                  i18n: {
                    millisecond: 'ms',
                    second: 's',
                    minute: 'min',
                    hour: 'h',
                    day: 'd',
                    validation_negative_number: 'Negative values not allowed'
                  },
                  displayed_magnitudes: ['day', 'hour', 'minute', 'second'],
                  input_hint: null,
                  type: 'time_span'
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            cleanup_abandoned_host_files: 2592000.0
          },
          default_value: {
            cleanup_abandoned_host_files: 2592000.0
          },
          modified: false,
          site_overrides: []
        },
        {
          name: 'site_piggyback_hub',
          spec: {
            title: 'Enable piggyback-hub',
            help: 'Enable the piggyback-hub to send/receive piggyback data to/from other sites.',
            validators: [],
            label: '',
            text_on: 'on',
            text_off: 'off',
            type: 'boolean_choice'
          },
          value: false,
          default_value: false,
          modified: false,
          site_overrides: []
        },
        {
          name: 'site_mkeventd',
          spec: {
            title: 'Event Console',
            help: 'This option enables the Event Console - The event processing and classification daemon of Checkmk. You can also configure whether or not the Event Console shal listen for incoming SNMP traps or syslog messages. Please note that only a single Checkmk site per Checkmk server can listen for such messages.',
            validators: [],
            parameter_form: {
              title: 'Listen for incoming messages via',
              help: '',
              validators: [],
              i18n: {
                add: 'Add >',
                remove: '< Remove',
                add_all: 'Add all >>',
                remove_all: '<< Remove all',
                available_options: 'Available options',
                selected_options: 'Selected options',
                selected: 'Selected',
                no_elements_available: 'No elements available',
                no_elements_selected: 'No elements selected',
                autocompleter_loading: 'Loading',
                search_available_options: 'Search available options',
                search_selected_options: 'Search selected options',
                and_x_more: 'and %(count)s more'
              },
              show_toggle_all: false,
              type: 'checkbox_list_choice',
              elements: [
                {
                  name: 'SNMPTRAP',
                  title: 'Receive SNMP traps (UDP/162)'
                },
                {
                  name: 'SYSLOG',
                  title: 'Receive Syslog messages (UDP/514)'
                },
                {
                  name: 'SYSLOG_TCP',
                  title: 'Receive Syslog messages (TCP/514)'
                }
              ]
            },
            i18n: {
              label: 'Event Console enabled',
              none_label: 'Event Console disabled'
            },
            parameter_form_default_value: [
              {
                name: 'SYSLOG',
                title: 'Receive Syslog messages (UDP/514)'
              }
            ],
            type: 'optional_choice'
          },
          value: [
            {
              name: 'SYSLOG',
              title: 'Receive Syslog messages (UDP/514)'
            }
          ],
          default_value: [
            {
              name: 'SYSLOG',
              title: 'Receive Syslog messages (UDP/514)'
            }
          ],
          modified: false,
          site_overrides: []
        }
      ]
    },
    {
      icon: 'development',
      headline: 'Developer tools',
      subline: 'Settings for developing Checkmk',
      warning:
        'These are internal settings used by Checkmk developers. Do not change them unless you know what you are doing. There is a high risk that using these features will break your Checkmk site. Any changes here will result in your Checkmk site no longer being officially supported.',
      variables: [
        {
          name: 'vue_experimental_features',
          spec: {
            title: 'Vue experimental features',
            help: 'These settings only affect features that are currently under development.',
            validators: [],
            groups: [],
            no_elements_text: '(no parameters)',
            additional_static_elements: {},
            elements: [
              {
                name: 'rule_render_mode',
                required: true,
                group: null,
                default_value: '28e1990ecf99f31c23d958ae87836e94b41bae5a19717b30ad1b77c3dcd9dca4',
                render_only: false,
                parameter_form: {
                  title: 'Rule rendering mode',
                  help: 'Enable experimental rendering modes for form specs. Keep in mind that some form specs are always rendered in the frontend, regardless of this setting.',
                  validators: [],
                  no_elements_text: '',
                  frozen: false,
                  label: '',
                  input_hint: 'Please choose',
                  type: 'single_choice',
                  elements: [
                    {
                      name: '28e1990ecf99f31c23d958ae87836e94b41bae5a19717b30ad1b77c3dcd9dca4',
                      title: 'Frontend (vue rendering)'
                    },
                    {
                      name: '0b364039b3b352c4ad11747d2be5e64300c16b1317f8e53df284702c98e991cf',
                      title: 'Backend (legacy rendering)'
                    }
                  ]
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            rule_render_mode: '28e1990ecf99f31c23d958ae87836e94b41bae5a19717b30ad1b77c3dcd9dca4'
          },
          default_value: {
            rule_render_mode: '28e1990ecf99f31c23d958ae87836e94b41bae5a19717b30ad1b77c3dcd9dca4'
          },
          modified: false,
          site_overrides: []
        },
        {
          name: 'inject_js_profiling_code',
          spec: {
            title: 'Inject JavaScript profiling code',
            help: '',
            validators: [],
            label: '',
            text_on: 'on',
            text_off: 'off',
            type: 'boolean_choice'
          },
          value: false,
          default_value: false,
          modified: false,
          site_overrides: []
        },
        {
          name: 'profiling_options',
          spec: {
            title: 'Performance profiles',
            help: 'Controls the performance-profile feature. When enabled, profiled GUI requests and <tt>cmk --profile</tt> runs are stored under <tt>var/check_mk/profiles</tt> and the <b>Setup &gt; Maintenance &gt; Performance profiles</b> page becomes available with an interactive flamegraph viewer. <br><br>Note: the upload endpoint deserialises user-supplied cProfile bytes and is therefore restricted to administrators. Disable the feature on hardened deployments if untrusted admin sessions are a concern.',
            validators: [],
            groups: [],
            no_elements_text: '(no parameters)',
            additional_static_elements: {},
            elements: [
              {
                name: 'enabled',
                required: true,
                group: null,
                default_value: false,
                render_only: false,
                parameter_form: {
                  title: 'Enable performance profiles',
                  help: '',
                  validators: [],
                  label: 'Show the Performance profiles page and record profiled requests',
                  text_on: 'on',
                  text_off: 'off',
                  type: 'boolean_choice'
                }
              },
              {
                name: 'max_count',
                required: true,
                group: null,
                default_value: 100,
                render_only: false,
                parameter_form: {
                  title: 'Maximum number of stored profiles',
                  help: 'When a new profile is saved and this count is exceeded, the oldest profiles are removed first.',
                  validators: [
                    {
                      error_message: 'Number is not an integer value.',
                      type: 'is_integer'
                    },
                    {
                      min_value: 1,
                      max_value: null,
                      error_message: 'The minimum allowed value is 1.',
                      type: 'number_in_range'
                    }
                  ],
                  label: '',
                  unit: '',
                  input_hint: null,
                  type: 'integer'
                }
              },
              {
                name: 'max_age_days',
                required: false,
                group: null,
                default_value: 1,
                render_only: false,
                parameter_form: {
                  title: 'Maximum age of stored profiles',
                  help: 'Profiles older than this are discarded on the next save or housekeeping run. Leave unset to keep profiles indefinitely (count-based cap still applies).',
                  validators: [
                    {
                      error_message: 'Number is not an integer value.',
                      type: 'is_integer'
                    },
                    {
                      min_value: 1,
                      max_value: null,
                      error_message: 'The minimum allowed value is 1.',
                      type: 'number_in_range'
                    }
                  ],
                  label: '',
                  unit: 'days',
                  input_hint: null,
                  type: 'integer'
                }
              }
            ],
            type: 'dictionary'
          },
          value: {
            enabled: false,
            max_count: 100
          },
          default_value: {
            enabled: false,
            max_count: 100
          },
          modified: false,
          site_overrides: []
        },
        {
          name: 'load_frontend_vue',
          spec: {
            title: 'Inject frontend_vue files via vite client',
            help: 'If you change this to &#x27;inject&#x27; and there is no vite dev server running you may not be able to deactivate this option via UI, so be careful!',
            validators: [],
            no_elements_text: '',
            frozen: false,
            label: '',
            input_hint: 'Please choose',
            type: 'single_choice',
            elements: [
              {
                name: 'dacd0e5190a1f3403075296c7741647942c3d2efa8c0dc7fa5de66a3960ae2bc',
                title: 'Load JavaScript from shipped, static files'
              },
              {
                name: 'c86cac7c0b9fc287ff471bc34bef94e2a26544db95d8a93a2c999a7a6e902e18',
                title: 'Inject vite client to enable auto hot reloading'
              }
            ]
          },
          value: 'dacd0e5190a1f3403075296c7741647942c3d2efa8c0dc7fa5de66a3960ae2bc',
          default_value: 'dacd0e5190a1f3403075296c7741647942c3d2efa8c0dc7fa5de66a3960ae2bc',
          modified: false,
          site_overrides: []
        }
      ]
    }
  ]
} as GlobalSettingsApp
