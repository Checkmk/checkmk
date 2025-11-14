<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DataSize } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormDataSize from '@/form/private/forms/FormDataSize.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<DataSize>({
  type: 'data_size',
  label: 'some label',
  input_hint: 'some input hint',
  title: 'some title',
  help: 'some help',
  validators: [],
  displayed_magnitudes: ['B', 'KB', 'MB', 'GB', 'TB'],
  i18n: {
    choose_unit: 'Choose unit'
  }
})

const data = ref<[string, string]>(['100', 'MB'])

const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: ['5', 'GB']
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
  <FormDataSize v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
