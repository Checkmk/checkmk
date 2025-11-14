<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FixedValue } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormFixedValue from '@/form/private/forms/FormFixedValue.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<FixedValue>({
  type: 'fixed_value',
  label: null,
  value: 'This is a fixed value',
  title: 'some title',
  help: 'some help',
  validators: []
})

const data = ref('This is a fixed value')

const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: '5'
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
  <FormFixedValue v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
