<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import TopicsRenderer from '@/graph-designer/components/TopicsRenderer.vue'
import { ref } from 'vue'
import { type I18N } from '@/graph-designer/type_defs'
import { type Topic } from '@/graph-designer/components/type_defs'
import { type ValidationMessages } from '@/form'

const props = defineProps<{
  i18n: I18N
}>()

// Specs

const dataUnit = ref(['first_with_unit', null])
const specUnit = {
  type: 'cascading_single_choice',
  title: '',
  help: '',
  validators: [],
  elements: [
    {
      name: 'first_with_unit',
      title: props.i18n.graph_options.unit_first_with_unit,
      parameter_form: {
        type: 'fixed_value',
        title: '',
        help: '',
        validators: []
      },
      default_value: null
    },
    {
      name: 'custom',
      title: props.i18n.graph_options.unit_custom,
      parameter_form: {
        type: 'dictionary',
        title: '',
        help: '',
        validators: [],
        elements: [
          {
            ident: 'notation',
            required: true,
            parameter_form: {
              type: 'cascading_single_choice',
              title: props.i18n.graph_options.unit_custom_notation,
              help: '',
              validators: [],
              elements: [
                {
                  name: 'decimal',
                  title: props.i18n.graph_options.unit_custom_notation_decimal,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'si',
                  title: props.i18n.graph_options.unit_custom_notation_si,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'iec',
                  title: props.i18n.graph_options.unit_custom_notation_iec,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'standard_scientific',
                  title: props.i18n.graph_options.unit_custom_notation_standard_scientific,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'engineering_scientific',
                  title: props.i18n.graph_options.unit_custom_notation_engineering_scientific,
                  parameter_form: {
                    type: 'string',
                    title: props.i18n.graph_options.unit_custom_notation_symbol,
                    help: '',
                    validators: [],
                    input_hint: 'symbol',
                    field_size: 'SMALL'
                  },
                  default_value: ''
                },
                {
                  name: 'time',
                  title: props.i18n.graph_options.unit_custom_notation_time,
                  parameter_form: {
                    type: 'fixed_value',
                    title: '',
                    help: '',
                    validators: []
                  },
                  default_value: null
                }
              ]
            },
            default_value: { decimal: '' }
          },
          {
            ident: 'precision',
            required: true,
            parameter_form: {
              type: 'dictionary',
              title: props.i18n.graph_options.unit_custom_precision,
              help: '',
              validators: [],
              elements: [
                {
                  ident: 'rounding_mode',
                  required: true,
                  parameter_form: {
                    type: 'single_choice',
                    title: props.i18n.graph_options.unit_custom_precision_rounding_mode,
                    help: '',
                    validators: [],
                    elements: [
                      {
                        name: 'auto',
                        title: props.i18n.graph_options.unit_custom_precision_rounding_mode_auto
                      },
                      {
                        name: 'strict',
                        title: props.i18n.graph_options.unit_custom_precision_rounding_mode_strict
                      }
                    ],
                    frozen: false
                  },
                  default_value: 'auto'
                },
                {
                  ident: 'digits',
                  required: true,
                  parameter_form: {
                    type: 'float',
                    title: props.i18n.graph_options.unit_custom_precision_digits,
                    help: '',
                    validators: []
                  },
                  default_value: 2
                }
              ]
            },
            default_value: { rounding_mode: 'auto', digits: 2 }
          }
        ]
      },
      default_value: { notation: ['decimal', ''], precision: { rounding_mode: 'auto', digits: 2 } }
    }
  ]
}
const backendValidationUnit: ValidationMessages = []

const dataVerticalRange = ref(['auto', null])
const specVerticalRange = {
  type: 'cascading_single_choice',
  title: '',
  help: '',
  validators: [],
  elements: [
    {
      name: 'auto',
      title: props.i18n.graph_options.vertical_range_auto,
      parameter_form: {
        type: 'fixed_value',
        title: 'i18n:Title',
        help: '',
        validators: []
      }
    },
    {
      name: 'explicit',
      title: props.i18n.graph_options.vertical_range_explicit,
      parameter_form: {
        type: 'dictionary',
        title: '',
        help: '',
        validators: [],
        elements: [
          {
            ident: 'lower',
            required: true,
            parameter_form: {
              type: 'float',
              title: props.i18n.graph_options.vertical_range_explicit_lower,
              help: '',
              validators: []
            },
            default_value: 0.0
          },
          {
            ident: 'upper',
            required: true,
            parameter_form: {
              type: 'float',
              title: props.i18n.graph_options.vertical_range_explicit_upper,
              help: '',
              validators: []
            },
            default_value: 1.0
          }
        ]
      },
      default_value: { lower: 0.0, upper: 1.0 }
    }
  ]
}
const backendValidationVerticalRange: ValidationMessages = []

const dataMetricsWithZeroValues = ref(true)
const specMetricsWithZeroValues = {
  type: 'boolean_choice',
  title: '',
  help: '',
  validators: []
}
const backendValidationMetricsWithZeroValues: ValidationMessages = []

const topics: Topic[] = [
  {
    ident: 'graph_lines',
    title: props.i18n.topics.graph_lines,
    elements: [
      { ident: 'metric', title: props.i18n.topics.metric },
      { ident: 'scalar', title: props.i18n.topics.scalar },
      { ident: 'constant', title: props.i18n.topics.constant }
    ]
  },
  {
    ident: 'graph_operations',
    title: props.i18n.topics.graph_operations,
    elements: [
      { ident: 'operations', title: props.i18n.topics.operations },
      { ident: 'transformation', title: props.i18n.topics.transformation }
    ]
  },
  {
    ident: 'graph_options',
    title: props.i18n.topics.graph_options,
    elements: [
      { ident: 'unit', title: props.i18n.topics.unit },
      { ident: 'vertical_range', title: props.i18n.topics.vertical_range },
      {
        ident: 'metrics_with_zero_values',
        title: props.i18n.topics.metrics_with_zero_values
      }
    ]
  }
]
</script>

<template>
  <TopicsRenderer :topics="topics">
    <template #unit>
      <div>
        <FormEdit
          v-model:data="dataUnit"
          :spec="specUnit"
          :backend-validation="backendValidationUnit"
        />
      </div>
    </template>
    <template #vertical_range>
      <div>
        <FormEdit
          v-model:data="dataVerticalRange"
          :spec="specVerticalRange"
          :backend-validation="backendValidationVerticalRange"
        />
      </div>
    </template>
    <template #metrics_with_zero_values>
      <div>
        <FormEdit
          v-model:data="dataMetricsWithZeroValues"
          :spec="specMetricsWithZeroValues"
          :backend-validation="backendValidationMetricsWithZeroValues"
        />
      </div>
    </template>
  </TopicsRenderer>
</template>
