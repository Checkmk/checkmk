<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { LegacyValuespec } from '@/form/components/vue_formspec_components'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { select } from 'd3-selection'
import FormValidation from '@/form/components/FormValidation.vue'
import type { ValidationMessages } from '@/form/components/utils/validation'

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

onMounted(() => {
  // @ts-expect-error comes from different javascript file
  window['cmk'].forms.enable_dynamic_form_elements(legacyDOM.value!)
  // @ts-expect-error comes from different javascript file
  window['cmk'].valuespecs.initialize_autocompleters(legacyDOM.value!)
  select(legacyDOM.value!).selectAll('input,select').on('input.observer', collectData)
  collectData()
})

onBeforeUnmount(() => {
  select(legacyDOM.value!).selectAll('input').on('input.observer', null)
})

function collectData() {
  let result = Object.fromEntries(new FormData(legacyDOM.value))
  data.value = {
    input_context: result,
    varprefix: props.spec.varprefix
  }
}
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <form
    ref="legacyDOM"
    style="background: #595959"
    class="legacy_valuespec"
    v-html="spec.input_html"
  ></form>
  <!--eslint-enable-->
  <FormValidation :validation="validation"></FormValidation>
</template>
