<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { OptionalChoice, String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormOptionalChoice from '@/form/components/forms/FormOptionalChoice.vue'

defineProps<{ screenshotMode: boolean }>()

const embeddedSpec: String = {
  type: 'string',
  title: 'some string title',
  help: 'some string help',
  label: null,
  i18n_base: { required: 'required' },
  input_hint: 'some string input hint',
  field_size: 'SMALL',
  autocompleter: null,
  validators: []
}

const spec = ref<OptionalChoice>({
  type: 'optional_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  i18n: {
    label: 'i18n label',
    none_label: 'i18n none label'
  },
  parameter_form_default_value: 'default_value',
  parameter_form: embeddedSpec
})
const data = ref<null | string>(null)
</script>

<template>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormOptionalChoice v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
