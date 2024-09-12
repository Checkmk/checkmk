<script lang="ts">
import { h, type VNode, defineComponent, type PropType } from 'vue'
import type {
  Components,
  Dictionary,
  FormSpec,
  List,
  TimeSpan,
  SingleChoice,
  CascadingSingleChoice,
  LegacyValuespec,
  FixedValue,
  BooleanChoice,
  MultilineText,
  MultipleChoice,
  Password,
  Tuple,
  OptionalChoice,
  CommentTextArea
} from '@/form/components/vue_formspec_components'
import {
  groupDictionaryValidations,
  groupIndexedValidations,
  type ValidationMessages
} from '@/form/components/utils/validation'
import { splitToUnits, getSelectedMagnitudes, ALL_MAGNITUDES } from './utils/timeSpan'

const ERROR_BACKGROUND_COLOR = 'rgb(252, 85, 85)'

function renderForm(
  formSpec: FormSpec,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode | null {
  switch (formSpec.type as Components['type']) {
    case 'dictionary':
      return renderDict(formSpec as Dictionary, value as Record<string, unknown>, backendValidation)
    case 'time_span':
      return renderTimeSpan(formSpec as TimeSpan, value as number)
    case 'string':
    case 'integer':
    case 'float':
      return renderSimpleValue(formSpec, value as string, backendValidation)
    case 'single_choice':
      return renderSingleChoice(formSpec as SingleChoice, value as unknown, backendValidation)
    case 'list':
      return renderList(formSpec as List, value as unknown[], backendValidation)
    case 'cascading_single_choice':
      return renderCascadingSingleChoice(
        formSpec as CascadingSingleChoice,
        value as [string, unknown],
        backendValidation
      )
    case 'legacy_valuespec':
      return renderLegacyValuespec(formSpec as LegacyValuespec, value, backendValidation)
    case 'fixed_value':
      return renderFixedValue(formSpec as FixedValue)
    case 'boolean_choice':
      return renderBooleanChoice(formSpec as BooleanChoice, value as boolean)
    case 'multiline_text':
      return renderMultilineText(formSpec as MultilineText, value as string)
    case 'comment_text_area':
      return renderMultilineText(formSpec as CommentTextArea, value as string)
    case 'data_size':
      return renderDataSize(value as [string, string])
    case 'catalog':
      return h('div', 'Catalog does not support readonly')
    case 'multiple_choice':
      return renderMultipleChoice(formSpec as MultipleChoice, value as string[])
    case 'password':
      return renderPassword(formSpec as Password, value as (string | boolean)[])
    case 'tuple':
      return renderTuple(formSpec as Tuple, value as unknown[])
    case 'optional_choice':
      return renderOptionalChoice(formSpec as OptionalChoice, value as unknown[])
    case 'simple_password':
      return renderSimplePassword()
    default:
      return null
  }
}

function renderSimplePassword(): VNode {
  return h('div', ['******'])
}

function renderOptionalChoice(
  formSpec: OptionalChoice,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode | null {
  if (value === null) {
    return h('div', formSpec.i18n.none_label)
  }
  const embeddedMessages: ValidationMessages = []
  const localMessages: ValidationMessages = []
  backendValidation.forEach((msg) => {
    if (msg['location'].length > 0) {
      embeddedMessages.push({
        location: msg.location.slice(1),
        message: msg.message,
        invalid_value: msg.invalid_value
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
  const tupleResults: VNode[] = []
  tupleValidations.forEach((validation: string) => {
    tupleResults.push(h('label', [validation]))
  })

  const elementResults: VNode[] = []
  formSpec.elements.forEach((element, index) => {
    const renderResult = renderForm(element, value[index], elementValidations[index])
    if (renderResult === null) {
      return
    }
    elementResults.push(h('td', renderResult))
    elementResults.push(h('td', ', '))
  })
  elementResults.pop() // Remove last comma
  tupleResults.push(h('table', h('tr', elementResults)))
  return h('span', tupleResults)
}

function renderMultipleChoice(formSpec: MultipleChoice, value: string[]): VNode {
  let nameToTitle: Record<string, string> = {}
  for (const element of formSpec.elements) {
    nameToTitle[element.name] = element.title
  }

  const maxEntries = 10
  const textTokens: string[] = []

  // WIP: no i18n...
  for (let [index, entry] of value.entries()) {
    if (index >= maxEntries) {
      break
    }
    textTokens.push(nameToTitle[entry]!)
  }
  let infoText = textTokens.join(', ')
  if (value.length > maxEntries) {
    infoText += ` and ${value.length - maxEntries} more`
  }
  return h('div', infoText)
}

function renderDataSize(value: [string, string]): VNode {
  return h('div', [h('span', value[0]), h('span', ' '), h('span', value[1])])
}

function renderMultilineText(formSpec: MultilineText, value: string): VNode {
  const lines: VNode[] = []
  value.split('\n').forEach((line) => {
    lines.push(h('span', { style: 'white-space: pre-wrap' }, line))
    lines.push(h('br'))
  })

  const style = formSpec.monospaced ? 'font-family: monospace, sans-serif' : ''
  return h('div', { style: style }, lines)
}

function renderBooleanChoice(formSpec: BooleanChoice, value: boolean): VNode {
  return h('div', value ? formSpec.text_on : formSpec.text_off)
}

function renderFixedValue(formSpec: FixedValue): VNode {
  const shownValue = formSpec.label ? formSpec.label : formSpec.value
  return h('div', shownValue as string)
}

function renderDict(
  formSpec: Dictionary,
  value: Record<string, unknown>,
  backendValidation: ValidationMessages
): VNode {
  const dictElements: VNode[] = []
  // Note: Dictionary validations are not shown
  const [, elementValidations] = groupDictionaryValidations(formSpec.elements, backendValidation)
  formSpec.elements.map((element) => {
    if (value[element.ident] == undefined) {
      return
    }

    const elementForm = renderForm(
      element.parameter_form,
      value[element.ident],
      elementValidations[element.ident] || []
    )
    if (elementForm === null) {
      return
    }
    dictElements.push(
      h('tr', [
        h('th', `${element.parameter_form.title}: `),
        h('td', { style: 'align: left' }, [elementForm])
      ])
    )
  })
  return h(
    'table',
    { class: formSpec.layout === 'two_columns' ? 'form-readonly__dictionary--two_columns' : '' },
    dictElements
  )
}

function computeUsedValue(
  value: unknown,
  backendValidation: ValidationMessages = []
): [string, boolean, string] {
  if (backendValidation.length > 0) {
    return [backendValidation[0]!.invalid_value as string, true, backendValidation[0]!.message]
  }
  return [value as string, false, '']
}

function renderSimpleValue(
  _formSpec: FormSpec,
  value: string,
  backendValidation: ValidationMessages = []
): VNode {
  let [usedValue, isError, errorMessage] = computeUsedValue(value, backendValidation)
  return h(
    'div',
    isError ? { style: ERROR_BACKGROUND_COLOR } : {},
    isError ? [`${usedValue} - ${errorMessage}`] : [usedValue]
  )
}

function renderPassword(formSpec: Password, value: (string | boolean)[]): VNode {
  if (value[0] === 'explicit_password') {
    return h('div', [`${formSpec.i18n.explicit_password}, ******`])
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
  formSpec: SingleChoice,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode {
  for (const element of formSpec.elements) {
    if (element.name === value) {
      return h('div', [element.title])
    }
  }

  // Value not found in valid values. Try to show error
  let [usedValue, isError, errorMessage] = computeUsedValue(value, backendValidation)
  if (isError) {
    return h('div', { style: `background: ${ERROR_BACKGROUND_COLOR}` }, [
      `${usedValue} - ${errorMessage}`
    ])
  }

  // In case no validation message is present, we still want to show raw_value
  // (This should not happen in production, but is useful for debugging)
  return h('div', { style: `background: ${ERROR_BACKGROUND_COLOR}` }, [
    `${usedValue} - Invalid value`
  ])
}

function renderList(
  formSpec: List,
  value: unknown[],
  backendValidation: ValidationMessages
): VNode | null {
  const [listValidations, elementValidations] = groupIndexedValidations(
    backendValidation,
    value.length
  )
  if (!value) {
    return null
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
  return h('ul', { style: 'display: contents' }, listResults)
}

function renderCascadingSingleChoice(
  formSpec: CascadingSingleChoice,
  value: [string, unknown],
  backendValidation: ValidationMessages
): VNode | null {
  for (const element of formSpec.elements) {
    if (element.name === value[0]) {
      return h('div', [
        h('div', formSpec.title),
        h('div', element.title),
        renderForm(element.parameter_form, value[1], backendValidation)
      ])
    }
  }
  return null
}

function renderLegacyValuespec(
  formSpec: LegacyValuespec,
  _value: unknown,
  backendValidation: ValidationMessages
): VNode {
  return h('div', [
    h('div', {
      style: 'background: #595959',
      class: 'legacy_valuespec',
      innerHTML: formSpec.readonly_html
    }),
    h('div', { validation: backendValidation })
  ])
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
.form-readonly__dictionary--two_columns > tr > th {
  width: 130px;
  padding-right: 16px;
  font-weight: var(--font-weight-bold);
}
</style>
