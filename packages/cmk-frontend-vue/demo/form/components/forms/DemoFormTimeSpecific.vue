<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TimeSpecific } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormTimeSpecific from '@/form/private/forms/FormTimeSpecific.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<TimeSpecific>({
  type: 'time_specific',
  time_specific_values_key: 'tp_values',
  default_value_key: 'tp_default_value',
  title: 'some title',
  help: 'some help',
  validators: [],
  i18n: {
    enable: 'Enable',
    disable: 'Disable'
  },
  parameter_form_enabled: {
    title: 'Enabled Form',
    help: 'Form when time-specific is enabled',
    validators: []
  },
  parameter_form_disabled: {
    title: 'Disabled Form',
    help: 'Form when time-specific is disabled',
    validators: []
  }
})

const data = ref<{ tp_default_value: unknown; tp_values: unknown[] } | unknown>({
  tp_default_value: 'default',
  tp_values: []
})

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
  <FormTimeSpecific v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
