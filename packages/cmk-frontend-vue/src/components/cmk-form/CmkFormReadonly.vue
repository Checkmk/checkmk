<script setup lang="ts">
import { h, ref, type VNode, watch } from 'vue'
import type {
  Dictionary,
  FormSpec,
  List,
  SingleChoice,
  CascadingSingleChoice,
  LegacyValuespec,
  ValidationMessage,
  Components
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
    rendered.value = render_form(props.spec, data.value, props.backendValidation)
  },
  { deep: true, immediate: true }
)

function render_form(
  form_spec: FormSpec,
  value: unknown,
  backendValidation: ValidationMessages = []
): VNode | null {
  switch (form_spec.type as Components['type']) {
    case 'dictionary':
      return render_dict(
        form_spec as Dictionary,
        value as Record<string, unknown>,
        backendValidation
      )
    case 'string':
    case 'integer':
    case 'float':
      return render_simple_value(form_spec, value as string, backendValidation)
    case 'single_choice':
      return render_single_choice(form_spec as SingleChoice, value as string, backendValidation)
    case 'list':
      return render_list(form_spec as List, value as unknown[], backendValidation)
    case 'cascading_single_choice':
      return render_cascading_single_choice(
        form_spec as CascadingSingleChoice,
        value as [string, unknown],
        backendValidation
      )
    case 'legacy_valuespec':
      return render_legacy_valuespec(form_spec as LegacyValuespec, value, backendValidation)
  }
}

function render_dict(
  form_spec: Dictionary,
  value: Record<string, unknown>,
  backendValidation: ValidationMessages
): VNode {
  const dictElements: VNode[] = []
  // Note: Dictionary validations are not shown
  const [, elementValidations] = groupDictionaryValidations(form_spec.elements, backendValidation)
  form_spec.elements.map((element) => {
    if (value[element.ident] == undefined) {
      return
    }

    const elementForm = render_form(
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

function compute_used_value(
  value: unknown,
  backendValidation: ValidationMessages = []
): [string, boolean, string] {
  if (backendValidation.length > 0) {
    return [backendValidation[0]!.invalid_value as string, true, backendValidation[0]!.message]
  }
  return [value as string, false, '']
}

function render_simple_value(
  _form_spec: FormSpec,
  value: string,
  backendValidation: ValidationMessages = []
): VNode {
  let [usedValue, isError, errorMessage] = compute_used_value(value, backendValidation)
  return h(
    'div',
    isError ? { style: ERROR_BACKGROUND_COLOR } : {},
    isError ? [`${usedValue} - ${errorMessage}`] : [usedValue]
  )
}

function render_single_choice(
  form_spec: SingleChoice,
  value: string,
  backendValidation: ValidationMessages = []
): VNode {
  for (const element of form_spec.elements) {
    if (element.name === value) {
      return h('div', [element.title])
    }
  }

  // Value not found in valid values. Try to show error
  let [usedValue, isError, errorMessage] = compute_used_value(value, backendValidation)
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

function render_list(
  form_spec: List,
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
  const listResults = [h('label', [form_spec.element_template.title])]
  listValidations.forEach((validation: ValidationMessage) => {
    listResults.push(h('label', [validation.message]))
  })

  for (let i = 0; i < value.length; i++) {
    listResults.push(
      h('li', [
        render_form(
          form_spec.element_template,
          value[i],
          elementValidations[i] ? elementValidations[i] : []
        )
      ])
    )
  }
  return h('ul', { style: 'display: contents' }, listResults)
}

function render_cascading_single_choice(
  form_spec: CascadingSingleChoice,
  value: [string, unknown],
  backendValidation: ValidationMessages
): VNode | null {
  for (const element of form_spec.elements) {
    if (element.name === value[0]) {
      return h('div', [
        h('div', form_spec.title),
        h('div', element.title),
        render_form(element.parameter_form, value[1], backendValidation)
      ])
    }
  }
  return null
}

function render_legacy_valuespec(
  form_spec: LegacyValuespec,
  _value: unknown,
  backendValidation: ValidationMessages
): VNode {
  return h('div', [
    h('div', {
      style: 'background: #595959',
      class: 'legacy_valuespec',
      innerHTML: form_spec.readonly_html
    }),
    h('div', { validation: backendValidation })
  ])
}
</script>

<template>
  <component :is="rendered"></component>
</template>
