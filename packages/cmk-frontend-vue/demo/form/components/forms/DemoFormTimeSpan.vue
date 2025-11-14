<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TimeSpan } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormTimeSpan from '@/form/private/forms/FormTimeSpan/FormTimeSpan.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<TimeSpan>({
  type: 'time_span',
  label: 'some label',
  input_hint: 60,
  title: 'some title',
  help: 'some help',
  validators: [],
  displayed_magnitudes: ['second', 'minute', 'hour', 'day'],
  i18n: {
    millisecond: 'Millisecond',
    second: 'Second',
    minute: 'Minute',
    hour: 'Hour',
    day: 'Day',
    validation_negative_number: 'Value must be positive'
  }
})

const data = ref<number | null>(3600)

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
  <FormTimeSpan v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
