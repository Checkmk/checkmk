<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type {
  BinaryConditionChoices,
  BinaryConditionChoicesItem,
  BinaryConditionChoicesValue,
  BooleanChoice,
  CascadingSingleChoice,
  CheckboxListChoice,
  Components,
  ConditionChoices,
  ConditionChoicesValue,
  ConditionGroup,
  Dictionary,
  DictionaryElement,
  DictionaryGroup,
  DualListChoice,
  FileUpload,
  FixedValue,
  Float,
  FormSpec,
  Integer,
  Labels,
  LegacyValuespec,
  List,
  ListOfStrings,
  MetricBackendCustomQuery,
  MultilineText,
  MultipleChoiceElement,
  Oauth2ConnectionSetup,
  OptionalChoice,
  Password,
  SingleChoice,
  SingleChoiceElement,
  TimeSpan,
  TimeSpanTimeMagnitude,
  TimeSpecific,
  Tuple,
  TwoColumnDictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type PropType, type Ref, type VNode, defineComponent, h } from 'vue'

import usei18n from '@/lib/i18n'

import type { DualListElement } from '@/components/CmkDualList'
import {
  ALL_MAGNITUDES,
  getSelectedMagnitudes,
  splitToUnits
} from '@/components/user-input/CmkTimeSpan/timeSpan'

import type { CheckboxListChoiceElement } from '@/form/private/forms/FormCheckboxListChoice.vue'
import type { FileUploadData } from '@/form/private/forms/FormFileUpload.vue'
import FormLabelsLabel from '@/form/private/forms/FormLabelsLabel.vue'
import {
  type ValidationMessages,
  groupIndexedValidations,
  groupNestedValidations
} from '@/form/private/validation'

import {
  type Operator,
  type OperatorI18n,
  translateOperator
} from './private/forms/FormConditionChoices/utils'

const { _t } = usei18n()

function renderForm(
  formSpec: FormSpec,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode {
  switch ((formSpec as Components).type) {
    case 'dictionary':
      return renderDict(
        formSpec as Dictionary,
        'one_column',
        value as Record<string, unknown>,
        backendValidation
      )
    case 'two_column_dictionary':
      return renderDict(
        formSpec as TwoColumnDictionary,
        'two_columns',
        value as Record<string, unknown>,
        backendValidation
      )
    case 'time_span':
      return renderTimeSpan(formSpec as TimeSpan, value as number)
    case 'string':
    case 'integer':
      return renderIntegerUnit(formSpec as Integer, value as number)
    case 'float':
      return renderFloatUnit(formSpec as Float, value as number)
    case 'metric':
    case 'regex':
    case 'date_picker':
    case 'time_picker':
      return renderSimpleValue(formSpec, value as string, backendValidation)
    case 'single_choice_editable':
    case 'single_choice':
      return renderSingleChoice(formSpec as SingleChoice, value as unknown, backendValidation)
    case 'list':
    case 'list_unique_selection':
      return renderList(formSpec as List, value as unknown[], backendValidation)
    case 'list_of_strings':
      return renderListOfStrings(formSpec as ListOfStrings, value as unknown[], backendValidation)
    case 'cascading_single_choice':
      return renderCascadingSingleChoice(
        formSpec as CascadingSingleChoice,
        value as [string, unknown],
        backendValidation
      )
    case 'condition_choices':
      return renderConditionChoices(formSpec as ConditionChoices, value as ConditionChoicesValue[])
    case 'binary_condition_choices':
      return renderBinaryConditionChoices(
        formSpec as BinaryConditionChoices,
        value as BinaryConditionChoicesValue
      )
    case 'legacy_valuespec':
      return renderLegacyValuespec(formSpec as LegacyValuespec, value, backendValidation)
    case 'fixed_value':
      return renderFixedValue(formSpec as FixedValue)
    case 'boolean_choice':
      return renderBooleanChoice(formSpec as BooleanChoice, value as boolean)
    case 'multiline_text':
    case 'comment_text_area':
      return renderMultilineText(formSpec as MultilineText, value as string)
    case 'data_size':
      return renderDataSize(value as [string, string])
    case 'catalog':
      return h('div', 'Catalog does not support readonly')
    case 'dual_list_choice':
      return renderDualListChoice(formSpec as DualListChoice, value as DualListElement[])
    case 'checkbox_list_choice':
      return renderCheckboxListChoice(
        formSpec as CheckboxListChoice,
        value as CheckboxListChoiceElement[]
      )
    case 'password':
      return renderPassword(formSpec as Password, value as (string | boolean)[])
    case 'tuple':
      return renderTuple(formSpec as Tuple, value as unknown[])
    case 'optional_choice':
      return renderOptionalChoice(formSpec as OptionalChoice, value as unknown[])
    case 'simple_password':
      return renderSimplePassword()
    case 'labels':
      return renderLabels(formSpec as Labels, value as Record<string, string>)
    case 'time_specific':
      return renderTimeSpecific(formSpec as TimeSpecific, value, backendValidation)
    case 'file_upload':
      return renderFileUpload(formSpec as FileUpload, value as FileUploadData)
    case 'metric_backend_custom_query':
      return renderMetricBackendCustomQuery(value as MetricBackendCustomQuery)
    case 'dcd_metric_backend_filter':
      return h('div', 'DCD Metric Backend Filter does not support readonly')
    case 'oauth2_connection_setup':
      return renderOAuth2ConnectionSetup(formSpec as Oauth2ConnectionSetup, value)
    // Do not add a default case here. This is intentional to make sure that all form types are covered.
  }
}

function renderSimplePassword(): VNode {
  return h('div', ['******'])
}

function renderFileUpload(_formSpec: FileUpload, value: FileUploadData): VNode {
  return h('div', [value.file_name])
}

function renderOAuth2ConnectionSetup(formSpec: Oauth2ConnectionSetup, value: unknown): VNode {
  return renderForm(formSpec.form_spec, value)
}

function renderMetricBackendCustomQuery(value: MetricBackendCustomQuery): VNode {
  const rows: VNode[] = []

  if (value.metric_name) {
    rows.push(
      h('tr', [h('td', { class: 'dict_title' }, ['Metric:']), h('td', [value.metric_name])])
    )
  }

  const renderAttributes = (
    title: string,
    attributes: typeof value.resource_attributes
  ): VNode | null => {
    if (!attributes || attributes.length === 0) {
      return null
    }
    const attributeText = attributes.map((attr) => `${attr.key}:${attr.value}`).join(', ')
    return h('tr', [h('td', { class: 'dict_title' }, [`${title}:`]), h('td', [attributeText])])
  }

  const resourceRow = renderAttributes('Resource Attributes', value.resource_attributes)
  if (resourceRow) {
    rows.push(resourceRow)
  }

  const scopeRow = renderAttributes('Scope Attributes', value.scope_attributes)
  if (scopeRow) {
    rows.push(scopeRow)
  }

  const dataPointRow = renderAttributes('Data Point Attributes', value.data_point_attributes)
  if (dataPointRow) {
    rows.push(dataPointRow)
  }

  const timeSpan = []
  const i18Magnitudes: Partial<Record<TimeSpanTimeMagnitude, string | Ref<string>>> = {
    hour: _t('Hours'),
    minute: _t('Minutes'),
    second: _t('Seconds')
  }
  const values = splitToUnits(
    value.aggregation_lookback,
    getSelectedMagnitudes(['hour', 'minute', 'second'])
  )
  for (const [magnitude] of ALL_MAGNITUDES) {
    const v = values[magnitude]
    if (v !== undefined) {
      const i18Magnitude = i18Magnitudes[magnitude]
      const text = (i18Magnitude as Ref<string>)?.value || (i18Magnitude as string)
      timeSpan.push(`${v} ${text}`)
    }
  }
  rows.push(
    h('tr', [
      h('td', { class: 'dict_title' }, ['Aggregation lookback:']),
      h('td', timeSpan.join(' '))
    ])
  )

  rows.push(
    h('tr', [
      h('td', { class: 'dict_title' }, ['Percentile (histograms):']),
      h('td', [`${value.aggregation_histogram_percentile} %`])
    ])
  )

  rows.push(
    h('tr', [
      h('td', { class: 'dict_title' }, ['Service name template:']),
      h('td', [value.service_name_template])
    ])
  )

  return h('table', { class: 'form-readonly__dictionary' }, rows)
}

function renderOptionalChoice(
  formSpec: OptionalChoice,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode {
  if (value === null) {
    return h('div', h('i', formSpec.i18n.none_label))
  }
  const embeddedMessages: ValidationMessages = []
  const localMessages: ValidationMessages = []
  backendValidation.forEach((msg) => {
    if (msg['location'].length > 0) {
      embeddedMessages.push({
        location: msg.location.slice(1),
        message: msg.message,
        replacement_value: msg.replacement_value
      })
    } else {
      localMessages.push(msg)
    }
  })

  const errorFields: VNode[] = []
  localMessages.forEach((msg) => {
    errorFields.push(h('label', [msg.message]))
  })

  const embeddedResult = renderForm(formSpec.parameter_form, value, embeddedMessages)
  return h('div', [errorFields.concat(embeddedResult ? [embeddedResult] : [])])
}

function renderTuple(
  formSpec: Tuple,
  value: unknown[],
  backendValidation: ValidationMessages = []
): VNode {
  const [tupleValidations, elementValidations] = groupIndexedValidations(
    backendValidation,
    value.length
  )
  return h(
    'div',
    { class: `form-readonly__tuple form-readonly__tuple__layout-${formSpec.layout}` },
    [
      ...tupleValidations.map((validation: string) => {
        return h('label', [validation])
      }),
      ...formSpec.elements.map((element, index) => {
        // @ts-expect-error label does not exist on all element
        const title: string = element.title || element['label']
        return h('span', [
          formSpec.show_titles && title ? `${title}: ` : h([]),
          renderForm(element, value[index], elementValidations[index]),
          index !== formSpec.elements.length - 1 && formSpec.layout === 'horizontal' ? ', ' : ''
        ])
      })
    ]
  )
}

function renderDualListChoice(formSpec: DualListChoice, value: DualListElement[]): VNode {
  let localElements: MultipleChoiceElement[] = formSpec.elements
  if (formSpec.autocompleter) {
    localElements = [...localElements, ...value]
  }
  return renderMultipleChoice(
    formSpec,
    localElements,
    value.map((element) => element.name)
  )
}

function renderCheckboxListChoice(
  formSpec: CheckboxListChoice,
  value: CheckboxListChoiceElement[]
): VNode {
  return renderMultipleChoice(
    formSpec,
    formSpec.elements,
    value.map((element) => element.name)
  )
}

function renderMultipleChoice(
  formSpec: DualListChoice | CheckboxListChoice,
  elements: MultipleChoiceElement[],
  value: string[]
): VNode {
  const nameToTitle: Record<string, string> = {}
  for (const element of elements) {
    nameToTitle[element.name] = element.title
  }

  const maxEntries = 5
  const textSpans: VNode[] = []

  // WIP: no i18n...
  for (const [index, entry] of value.entries()) {
    if (index >= maxEntries) {
      break
    }
    textSpans.push(h('span', nameToTitle[entry]!))
  }
  if (value.length > maxEntries) {
    const moreText = formSpec.i18n.and_x_more.replace('%s', `${value.length - maxEntries}`)
    textSpans.push(
      h('span', { class: 'form-readonly__multiple-choice__max-entries' }, ` ${moreText}`)
    )
  }
  return h('div', { class: 'form-readonly__multiple-choice' }, textSpans)
}

function renderDataSize(value: [string, string]): VNode {
  return h('div', [h('span', value[0]), h('span', ' '), h('span', value[1])])
}

function renderMultilineText(formSpec: MultilineText, value: string): VNode {
  const lines: VNode[] = []
  if (formSpec.label) {
    lines.push(h('span', formSpec.label))
    lines.push(h('br'))
  }

  value.split('\n').forEach((line) => {
    lines.push(h('span', { style: 'white-space: pre-wrap' }, line))
    lines.push(h('br'))
  })

  const style = formSpec.monospaced ? 'font-family: monospace, sans-serif' : ''
  return h('div', { style: style }, lines)
}

function renderBooleanChoice(formSpec: BooleanChoice, value: boolean): VNode {
  return h('div', [
    `${formSpec.label}${formSpec.label ? ': ' : ''}${value ? formSpec.text_on : formSpec.text_off}`
  ])
}

function renderFixedValue(formSpec: FixedValue): VNode {
  let shownValue = formSpec.value
  if (formSpec.label !== null) {
    shownValue = formSpec.label
  }
  return h('div', shownValue as string)
}

function renderIntegerUnit(formSpec: Integer, value: number): VNode {
  let shownValue = `${value}`
  if (formSpec.unit) {
    shownValue += ` ${formSpec.unit}`
  }
  return h('div', shownValue)
}
function renderFloatUnit(formSpec: Float, value: number): VNode {
  let shownValue = `${value}`
  if (formSpec.unit) {
    shownValue += ` ${formSpec.unit}`
  }
  return h('div', shownValue)
}

function renderDict(
  formSpec: Dictionary | TwoColumnDictionary,
  layout: 'one_column' | 'two_columns',
  value: Record<string, unknown>,
  backendValidation: ValidationMessages
): VNode {
  const dictElements: VNode[] = []
  // Note: Dictionary validations are not shown
  const [, elementValidations] = groupNestedValidations(formSpec.elements, backendValidation)

  const DICT_ELEMENT_NO_GROUP = '-ungrouped-'
  const groups: Record<string, DictionaryElement[]> = {}
  groups[DICT_ELEMENT_NO_GROUP] = []
  const groupByKey: Record<string, DictionaryGroup> = {}
  groupByKey[DICT_ELEMENT_NO_GROUP] = {
    key: DICT_ELEMENT_NO_GROUP,
    title: '',
    help: null,
    layout: 'vertical'
  }

  formSpec.elements.forEach((element) => {
    if (element.group === null) {
      groups[DICT_ELEMENT_NO_GROUP]!.push(element)
    } else {
      if (!groups[element.group.key!]) {
        groups[element.group.key!] = []
        groupByKey[element.group.key!] = element.group!
      }
      groups[element.group.key!]!.push(element)
    }
  })

  for (const [groupKey, groupElements] of Object.entries(groups)) {
    const elements: [string, VNode][] = []
    groupElements.forEach((element) => {
      if (value[element.name] === undefined) {
        return
      }

      const elementForm = renderForm(
        element.parameter_form,
        value[element.name],
        elementValidations[element.name] || []
      )
      if (elementForm === null) {
        return
      }

      elements.push([element.parameter_form.title, elementForm])
    })
    const group = groupByKey[groupKey]!
    const trProps: Record<string, string> = {}
    if (group.title) {
      dictElements.push(
        h('tr', [h('td', { colspan: 2, class: 'dict_group_title' }, [group.title])])
      )
      trProps['class'] = 'dict_group'
    }
    if (group.layout === 'vertical') {
      elements.forEach((element) => {
        if (element[0]) {
          dictElements.push(
            h('tr', trProps, [
              h('td', { class: 'dict_title' }, [`${element[0]}:`]),
              h('td', { class: 'dict_value' }, [element[1]])
            ])
          )
        } else {
          dictElements.push(h('tr', trProps, [h('td', { class: 'dict_value' }, [element[1]])]))
        }
      })
    } else {
      const headers: VNode[] = []
      const values: VNode[] = []
      elements.forEach((element) => {
        headers.push(h('td', { class: 'dict_title' }, [element[0]]))
        values.push(h('td', { class: 'dict_value' }, [element[1]]))
      })
      dictElements.push(h('tr', trProps, headers))
      dictElements.push(h('tr', trProps, values))
    }
  }

  const cssClasses = [
    'form-readonly__dictionary',
    layout === 'two_columns' ? 'form-readonly__dictionary--two_columns' : ''
  ]

  if (dictElements.length === 0) {
    dictElements.push(
      h('tr', [
        h('td', { class: 'dict_title' }, [formSpec.no_elements_text]),
        h('td', { class: 'dict_value' }, [])
      ])
    )
  }
  return h('table', { class: cssClasses }, dictElements)
}

function computeUsedValue(
  value: unknown,
  backendValidation: ValidationMessages = []
): [string, boolean, string] {
  if (backendValidation.length > 0) {
    return [backendValidation[0]!.replacement_value as string, true, backendValidation[0]!.message]
  }
  return [value as string, false, '']
}

function renderSimpleValue(
  _formSpec: FormSpec,
  value: string,
  backendValidation: ValidationMessages = []
): VNode {
  const [usedValue, isError, errorMessage] = computeUsedValue(value, backendValidation)
  const cssClasses = ['form-readonly__simple-value', isError ? 'form-readonly__error' : '']
  return h('div', { class: cssClasses }, isError ? [`${usedValue} - ${errorMessage}`] : [usedValue])
}

function renderPassword(formSpec: Password, value: (string | boolean)[]): VNode {
  if (value[0] === 'explicit_password') {
    return h('div', [`${formSpec.i18n.explicit_password}: ******`])
  }

  const storeChoice = formSpec.password_store_choices.find(
    (choice) => choice.password_id === value[1]
  )
  if (storeChoice) {
    return h('div', [`${formSpec.i18n.password_store}, ${storeChoice.name}`])
  } else {
    return h('div', [`${formSpec.i18n.password_store}, ${formSpec.i18n.password_choice_invalid}`])
  }
}

function renderTimeSpan(formSpec: TimeSpan, value: number): VNode {
  const result = []
  const values = splitToUnits(value, getSelectedMagnitudes(formSpec.displayed_magnitudes))
  for (const [magnitude] of ALL_MAGNITUDES) {
    const v = values[magnitude]
    if (v !== undefined) {
      result.push(`${v} ${formSpec.i18n[magnitude]}`)
    }
  }
  return h('div', [result.join(' ')])
}

function renderSingleChoice(
  formSpec: { elements: SingleChoiceElement[] },
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode {
  for (const element of formSpec.elements) {
    if (element.name === value) {
      return h('div', [element.title])
    }
  }

  // Value not found in valid values. Try to show error
  const [usedValue, isError, errorMessage] = computeUsedValue(value, backendValidation)
  if (isError) {
    return h('div', { class: 'form-readonly__error' }, [`${usedValue} - ${errorMessage}`])
  }

  // In case no validation message is present, we still want to show raw_value
  // (This should not happen in production, but is useful for debugging)
  return h('div', { class: 'form-readonly__error' }, [`${usedValue} - Invalid value`])
}

function renderList(
  formSpec: List,
  value: unknown[],
  backendValidation: ValidationMessages
): VNode {
  const [listValidations, elementValidations] = groupIndexedValidations(
    backendValidation,
    value.length
  )
  if (!value) {
    return h([])
  }
  const listResults = [h('label', [formSpec.element_template.title])]
  listValidations.forEach((validation: string) => {
    listResults.push(h('label', [validation]))
  })

  for (let i = 0; i < value.length; i++) {
    listResults.push(
      h('li', [
        renderForm(
          formSpec.element_template,
          value[i],
          elementValidations[i] ? elementValidations[i] : []
        )
      ])
    )
  }
  return h('ul', { class: 'form-readonly__list' }, listResults)
}

function renderListOfStrings(
  formSpec: ListOfStrings,
  value: unknown[],
  backendValidation: ValidationMessages
): VNode {
  const [listValidations, elementValidations] = groupIndexedValidations(
    backendValidation,
    value.length
  )
  if (!value) {
    return h([])
  }
  const listResults = [h('label', [formSpec.string_spec.title])]
  listValidations.forEach((validation: string) => {
    listResults.push(h('label', [validation]))
  })

  for (let i = 0; i < value.length; i++) {
    listResults.push(
      h('li', [
        renderForm(
          formSpec.string_spec,
          value[i],
          elementValidations[i] ? elementValidations[i] : []
        )
      ])
    )
  }
  // return h('ul', { style: 'display: contents' }, listResults)
  return h('ul', { class: 'form-readonly__list' }, listResults)
}

function renderCascadingSingleChoice(
  formSpec: CascadingSingleChoice,
  value: [string, unknown],
  backendValidation: ValidationMessages
): VNode {
  for (const element of formSpec.elements) {
    if (element.name === value[0]) {
      return h(
        'div',
        h('div', { class: `form-readonly__cascading-single-choice__layout-${formSpec.layout}` }, [
          // notification explicitly defines empty string title:
          h('div', { style: 'vertical-align: top;' }, element.title.concat(':')),
          h('div', [renderForm(element.parameter_form, value[1], backendValidation)])
        ])
      )
    }
  }
  return h([])
}

function renderTimeSpecific(
  formSpec: TimeSpecific,
  value: unknown,
  backendValidation: ValidationMessages
): VNode {
  const isActive = typeof value === 'object' && value !== null && 'tp_default_value' in value
  if (isActive) {
    return h('div', [renderForm(formSpec.parameter_form_enabled, value, backendValidation)])
  } else {
    return h('div', [renderForm(formSpec.parameter_form_disabled, value, backendValidation)])
  }
}

interface PreRenderedHtml {
  input_html: string
  readonly_html: string
}

function renderLegacyValuespec(
  _formSpec: LegacyValuespec,
  value: unknown,
  backendValidation: ValidationMessages
): VNode {
  return h('div', [
    h('div', {
      class: 'legacy_valuespec',
      innerHTML: (value as PreRenderedHtml).readonly_html
    }),
    h('div', { validation: backendValidation })
  ])
}

function renderConditionChoiceGroup(
  group: ConditionGroup,
  value: ConditionChoicesValue,
  i18n: OperatorI18n
): VNode {
  const condition = Object.values(value.value)[0] as string | string[]
  const conditionList = condition instanceof Array ? condition : [condition]
  const operator = translateOperator(i18n, Object.keys(value.value)[0] as Operator)
  return h('tr', [
    h('td', group.title.concat(':')),
    h('td', [
      h('table', { class: 'force-inline-th' }, [
        h('tbody', [
          h('th', h('b', { class: 'font-weight-normal' }, operator)),
          ...conditionList.map((cValue) =>
            h('tr', h('td', group.conditions.find((cGroup) => cGroup.name === cValue)?.title))
          )
        ])
      ])
    ])
  ])
}

function renderConditionChoices(formSpec: ConditionChoices, value: ConditionChoicesValue[]): VNode {
  return h('table', { class: 'form-readonly__table' }, [
    h('tbody', [
      value.map((v) => {
        const group = formSpec.condition_groups[v.group_name]
        if (group === undefined) {
          throw new Error('Invalid group')
        }
        return renderConditionChoiceGroup(group, v, formSpec.i18n)
      })
    ])
  ])
}

function renderBinaryConditionChoicesGroup(items: BinaryConditionChoicesItem[]): VNode {
  // TODO use translated texts
  const parts = []
  for (const [index, item] of items.entries()) {
    if (index === 0) {
      if (item.operator === 'not') {
        parts.push('not')
      }
    } else {
      if (item.operator === 'not') {
        parts.push('and not')
      } else {
        parts.push(item.operator)
      }
    }
    parts.push(item.label)
  }
  return h('td', `[ ${parts.join(' ')} ]`)
}

function renderBinaryConditionChoices(
  formSpec: BinaryConditionChoices,
  value: BinaryConditionChoicesValue
): VNode {
  // TODO use translated texts
  return h('table', { class: 'form-readonly__table' }, [
    h('tbody', [
      value.map((v, index) => {
        if (index === 0) {
          return h('tr', [
            h('td', `${formSpec.label}:`),
            renderBinaryConditionChoicesGroup(v.label_group)
          ])
        } else {
          return h('tr', [
            h('td', `{v.operator}:`),
            renderBinaryConditionChoicesGroup(v.label_group)
          ])
        }
      })
    ])
  ])
}

function renderLabels(formSpec: Labels, value: Record<string, string>): VNode {
  return h(
    'div',
    { class: 'form-readonly__labels' },
    Object.entries(value).map(([key, value]) => {
      return h(FormLabelsLabel, {
        labelSource: formSpec.label_source,
        value: `${key}: ${value}`
      })
    })
  )
}

export default defineComponent({
  props: {
    spec: { type: Object as PropType<FormSpec>, required: true },
    data: { type: null as unknown as PropType<unknown>, required: true },
    backendValidation: { type: Object as PropType<ValidationMessages>, required: true }
  },
  render() {
    return renderForm(this.spec, this.data, this.backendValidation)
  }
})
</script>

<style scoped>
/* stylelint-disable no-descending-specificity */

.form-readonly__error {
  background-color: var(--form-readonly-error-bg-color);
}

table.form-readonly__table {
  margin-top: 0;
  border-collapse: collapse;

  td {
    vertical-align: top;
    padding: 0 5px 0 0;
  }

  table {
    border-collapse: collapse;

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.force-inline-th > tbody {
      & > tr {
        display: inline-block;
        margin-top: -1px;

        & > td {
          display: inline-block !important;
          vertical-align: top;
          padding: 0 5px 0 0;
        }
      }

      & > th {
        display: inline-block;
        padding-right: 5px;
      }
    }
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .font-weight-normal {
    font-weight: normal;
  }
}

.form-readonly__simple-value {
  display: inline-block;
}

.form-readonly__dictionary {
  display: inline-table;
  border-spacing: 0;

  > tr {
    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    > td.dict_title {
      min-width: 20ch;
      max-width: 70ch;
      white-space: normal;
      overflow-wrap: break-word;
    }

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.dict_group {
      > td:first-child {
        padding-left: 8px;
      }
    }
  }

  > tr > td {
    vertical-align: top;
    padding-bottom: 2px;
    padding-right: 4px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-readonly__dictionary--two_columns > tr {
  line-height: 18px;

  > th {
    width: 130px;
    padding-right: 16px;
    font-weight: var(--font-weight-bold);
  }

  > td > .form-readonly__multiple-choice span {
    display: block;

    &::before {
      content: '';
    }
  }
}

.form-readonly__multiple-choice span {
  &:not(:first-child)::before {
    content: ', ';
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.form-readonly__multiple-choice__max-entries::before {
    content: '';
  }
}

.form-readonly__list {
  padding-left: 0 !important;
  list-style-position: inside;
  list-style-type: circle;

  > li {
    display: flex;
    padding-left: 0 !important;

    ul {
      margin-left: 5px;
    }
  }
}

.form-readonly__list > li > div {
  display: inline-block;
}

.form-readonly__labels {
  display: flex;
  flex-flow: row wrap;
  justify-content: start;
  align-items: center;
  gap: 5px 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-readonly__cascading-single-choice__layout-horizontal {
  margin-bottom: 4px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-readonly__cascading-single-choice__layout-horizontal > div {
  margin-right: var(--spacing-half);
  display: inline-block;
}

.form-readonly__tuple > span > * {
  display: inline;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-readonly__tuple__layout-horizontal > span {
  margin: 5px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.form-readonly__tuple__layout-vertical {
  padding: 3px 0;

  > span {
    display: block;
  }
}
</style>
