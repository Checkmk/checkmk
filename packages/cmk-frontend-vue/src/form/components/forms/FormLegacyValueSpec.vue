<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { LegacyValuespec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import FormValidation from '@/form/components/FormValidation.vue'
import type { ValidationMessages } from '@/form/components/utils/validation'

const QUERY_INPUT_OBSERVER = 'select,input,textarea'

const props = defineProps<{
  spec: LegacyValuespec
  backendValidation: ValidationMessages
}>()

const validation = ref<Array<string>>([])

watch(
  () => props.backendValidation,
  (newValidation: ValidationMessages) => {
    const validations: Array<string> = []
    newValidation.forEach((message) => {
      validations.push(message.message)
    })
    validation.value = validations
  },
  { immediate: true }
)

const data = defineModel<unknown>('data', { required: true })
const legacyDOM = ref<HTMLFormElement>()

const inputHtml = ref('')

interface PreRenderedHtml {
  input_html: string
  readonly_html: string
}

function executeInlineScripts() {
  legacyDOM.value!.querySelectorAll('script').forEach((element) => {
    // ListOf
    const reListOf = /cmk.valuespecs.listof_update_indices\("([^"]+)"\)/
    let match = element.innerHTML.match(reListOf)
    if (match) {
      // @ts-expect-error comes from different javascript file
      window['cmk'].valuespecs.listof_update_indices(match[1])
    }

    // ListOfStrings
    const reListOfStrings = /cmk.valuespecs.list_of_strings_init\(([^)]+)\)/
    match = element.innerHTML.match(reListOfStrings)
    if (match) {
      const argumentsArray = match[1]!.split(/\s*,\s*/).map((arg) => arg.trim())
      // @ts-expect-error comes from different javascript file
      window['cmk'].valuespecs.list_of_strings_init(
        JSON.parse(argumentsArray[0]!),
        JSON.parse(argumentsArray[1]!),
        JSON.parse(argumentsArray[2]!)
      )
    }

    // ListOfMultiple
    const reListOfMultiple = /cmk.valuespecs.listofmultiple_init\("([^"]+)"\)/
    match = element.innerHTML.match(reListOfMultiple)
    if (match) {
      // @ts-expect-error comes from different javascript file
      window['cmk'].valuespecs.listofmultiple_init(match[1])
    }

    // CascadingDropdown
    const reAddCascading = /cmk.valuespecs.add_cascading_sub_valuespec_parameters(\([^)]+\))/
    match = element.innerHTML.match(reAddCascading)
    if (match) {
      const argumentsArray = JSON.parse(match[1]!.replace('(', '[').replace(')', ']'))
      // @ts-expect-error comes from different javascript file
      window['cmk'].valuespecs.add_cascading_sub_valuespec_parameters(
        argumentsArray[0]!,
        argumentsArray[1]!
      )
    }
  })
}

onMounted(() => {
  inputHtml.value = (data.value as PreRenderedHtml).input_html
  // @ts-expect-error comes from different javascript file
  window['cmk'].forms.enable_dynamic_form_elements(legacyDOM.value!)
  // @ts-expect-error comes from different javascript file
  window['cmk'].valuespecs.initialize_autocompleters(legacyDOM.value!)

  nextTick(() => {
    executeInlineScripts()
  }).catch((error) => {
    console.error('Error while evaluating scripts in legacy valuespec', error)
  })

  updateEventListeners()

  const observer = new MutationObserver(() => {
    collectData()
    updateEventListeners()
  })

  observer.observe(legacyDOM.value!, {
    attributes: true,
    characterData: true,
    childList: true,
    subtree: true
  })

  // Always collect data on mount. Sometimes the observer is not triggered, when the
  // legacyDOM does not contain input/select elements - like the FixedValue Valuespec
  collectData()
})

onBeforeUnmount(() => {
  legacyDOM.value!.querySelectorAll(QUERY_INPUT_OBSERVER).forEach((element) => {
    element.removeEventListener('input', collectData)
  })
})

function updateEventListeners() {
  legacyDOM.value!.querySelectorAll(QUERY_INPUT_OBSERVER).forEach((element) => {
    // @ts-expect-error This is not a standard property, but used to track if the element already has an event listener
    if (element._has_event_listener) {
      return
    }

    // @ts-expect-error This is not a standard property, but used to track if the element already has an event listener
    element._has_event_listener = true
    element.addEventListener('input', collectData)
  })
}

function collectData() {
  const result = Object.fromEntries(new FormData(legacyDOM.value))
  data.value = {
    input_context: result,
    varprefix: props.spec.varprefix
  }
}
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <form ref="legacyDOM" class="legacy_valuespec" v-html="inputHtml"></form>
  <!--eslint-enable-->
  <FormValidation :validation="validation"></FormValidation>
</template>
