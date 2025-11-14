<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { SingleChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkSpace from '@/components/CmkSpace.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const data = ref<string | null>(null)

function getSingleChoiceSpec(): SingleChoice {
  return {
    type: 'single_choice',
    title: '',
    help: '',
    validators: [],
    no_elements_text: 'No Elements',
    frozen: false,
    label: 'some label',
    input_hint: 'input hint',
    elements: [
      {
        name: '1',
        title: 'Any'
      },
      {
        name: '2',
        title: 'UP'
      },
      {
        name: '3',
        title: 'DOWN'
      },
      {
        name: '4',
        title: 'UNREACHABLE'
      }
    ]
  }
}
function getSingleChoiceSpecNoElements(): SingleChoice {
  return {
    type: 'single_choice',
    title: '',
    help: '',
    validators: [],
    no_elements_text: 'No Elements',
    frozen: false,
    label: 'No Elements',
    input_hint: 'input hint',
    elements: []
  }
}
const showValidation = ref<boolean>(false)
const validation = computed((): ValidationMessages => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'General Inline Error Message',
        replacement_value: ''
      }
    ]
  } else {
    return []
  }
})
</script>

<template>
  <div>
    <div>
      <CmkCheckbox v-model="showValidation" label="show validation" />
    </div>

    <pre>{{ JSON.stringify(data) }}</pre>
    <FormEdit v-model:data="data" :spec="getSingleChoiceSpec()" :backend-validation="validation" />
    <CmkSpace size="medium" />
    <FormEdit
      v-model:data="data"
      :spec="getSingleChoiceSpecNoElements()"
      :backend-validation="validation"
    />
  </div>
</template>
