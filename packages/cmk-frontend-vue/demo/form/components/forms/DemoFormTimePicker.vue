<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TimePicker } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormTimePicker from '@/form/private/forms/FormTimePicker.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<TimePicker>({
  type: 'time_picker',
  label: 'some label',
  title: 'some title',
  help: 'some help',
  validators: []
})

const data = ref('')

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
  <FormTimePicker v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
