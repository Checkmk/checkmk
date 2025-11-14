<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { OptionalChoice, String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const embeddedSpec: String = {
  type: 'string',
  title: 'some string title',
  help: 'some string help',
  label: null,
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
const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: 5
      }
    ]
  } else {
    return []
  }
})

const showValidation = ref<boolean>(false)
</script>

<template>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
