/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  CascadingSingleChoice,
  Dictionary,
  FixedValue,
  Float,
  Integer,
  OptionalChoice,
  SingleChoice,
  Tuple
} from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { PredictionPeriods } from '@/mode-alerts/types'

const WEEKDAY = '6c47c99835b507ae0ddffd0df817fbdd30633b902a75e5296b3a9c01417c2ec2'

// Like the Setup page, the period choice offers option ids instead of the periods' names.
export const PREDICTION_PERIODS: PredictionPeriods = {
  [WEEKDAY]: 'day_of_week',
  '4473bc8a7aa356e29acba007e36b0c1a020aecf9a2bd2abdd653149148d02281': 'day_of_month',
  a1eb030a70c6436daf4afdf459972d059e8eef00686ad31e4afcb54674bc1ab6: 'hour_of_day',
  '73efc1f84e168a0b774891edc50827612a0d4ddac1768bbec7449f633c11b5ce': 'minute_of_hour'
}

const PERIOD_TITLES: Record<string, string> = {
  day_of_week: 'Day of the week',
  day_of_month: 'Day of the month',
  hour_of_day: 'Hour of the day',
  minute_of_hour: 'Minute of the hour'
}

// The ruleset's levels form, as the Setup page sends it, built like the backend builds it.

function float(title: string, unit: string = '', inputHint: string | null = '0.0'): Float {
  return {
    type: 'float',
    title,
    help: '',
    validators: [{ type: 'is_float', error_message: 'Number is not a float value.' }],
    label: '',
    unit,
    input_hint: inputHint
  }
}

function pair(warn: Float, crit: Float, help: string = ''): Tuple {
  return {
    type: 'tuple',
    title: '',
    help,
    validators: [],
    elements: [warn, crit],
    show_titles: true,
    layout: 'vertical'
  }
}

function cascading(
  title: string,
  elements: CascadingSingleChoice['elements']
): CascadingSingleChoice {
  return {
    type: 'cascading_single_choice',
    title,
    help: '',
    validators: [],
    elements,
    no_elements_text: '(No choices available)',
    label: null,
    input_hint: null,
    layout: 'vertical',
    button_group_size: 'medium'
  }
}

const period: SingleChoice = {
  type: 'single_choice',
  title: 'Base prediction on',
  help: 'Define the periodicity in which the repetition of the measured data is expected (monthly, weekly, daily or hourly)',
  validators: [],
  elements: Object.entries(PREDICTION_PERIODS).map(([name, periodName]) => ({
    name,
    title: PERIOD_TITLES[periodName]!
  })),
  no_elements_text: '',
  frozen: false,
  label: '',
  input_hint: 'Please choose'
}

const horizon: Integer = {
  type: 'integer',
  title: 'Length of historic data to consider',
  help: 'How many days in the past Checkmk should evaluate the measurement data',
  validators: [
    { type: 'is_integer', error_message: 'Number is not an integer value.' },
    {
      type: 'number_in_range',
      min_value: 1,
      max_value: null,
      error_message: 'The minimum allowed value is 1.'
    }
  ],
  label: '',
  unit: 'days',
  input_hint: null
}

const noLevels: FixedValue = {
  type: 'fixed_value',
  title: 'No levels',
  help: '',
  validators: [],
  label: 'Do not impose levels, always be OK',
  value: null
}

function levelsSpec(upper: boolean): CascadingSingleChoice {
  const [fixedWarn, fixedCrit] = upper
    ? ['Warning at', 'Critical at']
    : ['Warning below', 'Critical below']
  const [warn, crit] = upper
    ? ['Warning above', 'Critical above']
    : ['Warning below', 'Critical below']
  const bound: OptionalChoice = {
    type: 'optional_choice',
    title: 'Fixed limits',
    help: '',
    validators: [],
    parameter_form: pair(
      float(upper ? 'Warning level is at least' : 'Warning level is at most', '', '0'),
      float(upper ? 'Critical level is at least' : 'Critical level is at most', '', '0')
    ),
    i18n: { label: 'Set fixed limits', none_label: '' },
    parameter_form_default_value: ['', '']
  }
  const predictive: Dictionary = {
    type: 'dictionary',
    title: 'Predictive levels (only on CMC)',
    help: '',
    validators: [],
    groups: [],
    no_elements_text: '(no parameters)',
    additional_static_elements: {},
    elements: [
      { name: 'period', parameter_form: period, default_value: WEEKDAY },
      { name: 'horizon', parameter_form: horizon, default_value: 90 },
      {
        name: 'levels',
        default_value: ['absolute', ['', '']],
        parameter_form: cascading('Level definition in relation to the predicted value', [
          {
            name: 'absolute',
            title: 'Absolute difference',
            default_value: ['', ''],
            parameter_form: pair(float(warn), float(crit))
          },
          {
            name: 'relative',
            title: 'Relative difference',
            default_value: [10.0, 20.0],
            parameter_form: pair(float(warn, '%', null), float(crit, '%', null))
          },
          {
            name: 'stdev',
            title: 'Standard deviation difference',
            default_value: [2.0, 4.0],
            parameter_form: pair(
              float(warn, 'times the standard deviation', null),
              float(crit, 'times the standard deviation', null)
            )
          }
        ])
      },
      { name: 'bound', parameter_form: bound, default_value: null }
    ].map((element) => ({ ...element, required: true, group: null, render_only: false }))
  }
  return cascading(upper ? 'Upper levels' : 'Lower levels', [
    {
      name: 'fixed',
      title: 'Fixed levels',
      default_value: ['', ''],
      parameter_form: pair(float(fixedWarn), float(fixedCrit))
    },
    {
      name: 'no_levels',
      title: 'No levels',
      default_value: null,
      parameter_form: noLevels
    },
    {
      name: 'predictive',
      title: 'Predictive levels (only on CMC)',
      default_value: { period: WEEKDAY, horizon: 90, levels: ['absolute', ['', '']], bound: null },
      parameter_form: predictive
    }
  ])
}

export const THRESHOLDS_SPEC: Dictionary = {
  type: 'dictionary',
  title: '',
  help: '',
  validators: [],
  groups: [],
  no_elements_text: '(no parameters)',
  additional_static_elements: {},
  elements: [
    { name: 'upper_levels', parameter_form: levelsSpec(true) },
    { name: 'lower_levels', parameter_form: levelsSpec(false) }
  ].map((element) => ({
    ...element,
    required: false,
    group: null,
    default_value: ['fixed', ['', '']],
    render_only: false
  }))
}
