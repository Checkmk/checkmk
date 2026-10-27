<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CheckboxListChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { computed, ref } from 'vue'

import FormCheckboxListChoice, {
  type CheckboxListChoiceElement
} from '@/form/private/forms/FormCheckboxListChoice.vue'

defineProps<{ screenshotMode: boolean }>()

const spec: CheckboxListChoice = {
  type: 'checkbox_list_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  elements: [
    {
      name: 'some_name_1',
      title: 'some title 1'
    },
    {
      name: 'some_name_2',
      title: 'some title 2'
    }
  ],
  i18n: {
    and_x_more: 'i18n and_x_more'
  },
  no_element_label: ''
}

const data = ref<Array<CheckboxListChoiceElement>>([
  {
    name: 'some_name_1',
    title: 'some title 1'
  }
])
const showValidation = ref<boolean>(false)
const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: [
          {
            name: 'some_name_2',
            title: 'some title 2'
          }
        ]
      }
    ]
  } else {
    return []
  }
})
</script>

<template>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormCheckboxListChoice v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
