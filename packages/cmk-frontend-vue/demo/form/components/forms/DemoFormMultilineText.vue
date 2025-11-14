<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MultilineText } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import FormMultilineText from '@/form/private/forms/FormMultilineText.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<MultilineText>({
  type: 'multiline_text',
  label: 'some label',
  input_hint: 'some input hint',
  title: 'some title',
  help: 'some help',
  validators: [],
  macro_support: true,
  monospaced: false
})

const data = ref<string>('')

const validation = computed(() => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'some validation problem',
        replacement_value: 'replacement_value'
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
  <FormMultilineText v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
