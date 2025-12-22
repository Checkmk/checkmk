<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type BinaryConditionChoices,
  type BinaryConditionChoicesValue
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const spec: BinaryConditionChoices = {
  type: 'binary_condition_choices',
  title: 'some title',
  help: 'some help',
  validators: [],
  label: 'some label',
  conditions: [
    { name: 'Condition A', title: 'Condition A Title' },
    { name: 'Condition B', title: 'Condition B Title' }
  ]
}

const data = ref<BinaryConditionChoicesValue>([])

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
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
