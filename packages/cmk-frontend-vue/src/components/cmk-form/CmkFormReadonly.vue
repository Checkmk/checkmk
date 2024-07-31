<script setup lang="ts">
import { h, ref, type VNode, watch } from 'vue'
import type {
  Components,
  Dictionary,
  FormSpec,
  List,
  SingleChoice,
  CascadingSingleChoice,
  LegacyValuespec,
  ValidationMessage,
  FixedValue,
  BooleanChoice,
  MultilineText
} from '@/vue_formspec_components'
import {
  groupDictionaryValidations,
  groupListValidations,
  type ValidationMessages
} from '@/lib/validation'

const props = defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
const ERROR_BACKGROUND_COLOR = 'rgb(252, 85, 85)'

const rendered = ref<VNode | null>(null)
watch(
  [data],
  () => {
    rendered.value = renderForm(props.spec, data.value, props.backendValidation)
  },
  { deep: true, immediate: true }
)

function renderForm(
  formSpec: FormSpec,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode | null {
  switch (formSpec.type as Components['type']) {
    case 'dictionary':
      return renderDict(formSpec as Dictionary, value as Record<string, unknown>, backendValidation)
    case 'string':
    case 'integer':
    case 'float':
      return renderSimpleValue(formSpec, value as string, backendValidation)
    case 'single_choice':
      return renderSingleChoice(formSpec as SingleChoice, value as string, backendValidation)
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
  }
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
        h('td', `${element.parameter_form.title}: `),
        h('td', { style: 'align: left' }, [elementForm])
      ])
    )
  })
  return h('table', dictElements)
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

function renderSingleChoice(
  formSpec: SingleChoice,
  value: string,
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
  const [listValidations, elementValidations] = groupListValidations(
    backendValidation,
    value.length
  )
  if (!value) {
    return null
  }
  const listResults = [h('label', [formSpec.element_template.title])]
  listValidations.forEach((validation: ValidationMessage) => {
    listResults.push(h('label', [validation.message]))
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
</script>

<template>
  <component :is="rendered"></component>
</template>
