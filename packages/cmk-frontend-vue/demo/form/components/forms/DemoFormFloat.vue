<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Float } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormFloat from '@/form/private/forms/FormFloat.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<Float>({
  type: 'float',
  label: 'some label',
  input_hint: 'some input hint',
  unit: '%',
  title: 'some title',
  help: 'some help',
  validators: []
})

const data = ref<number>(10.2)

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
  <FormFloat v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
