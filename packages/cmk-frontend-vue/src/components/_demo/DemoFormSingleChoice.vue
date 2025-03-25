<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'

import type { SingleChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'

defineProps<{ screenshotMode: boolean }>()

const data = ref<string | null>(null)

function getSingleChoiceSpec(): SingleChoice {
  return {
    type: 'single_choice',
    title: '',
    help: '',
    i18n_base: { required: 'required' },
    validators: [],
    no_elements_text: '',
    frozen: false,
    label: 'some label',
    input_hint: 'Please choose',
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
</script>

<template>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormEdit v-model:data="data" :spec="getSingleChoiceSpec()" :backend-validation="[]" />
</template>

<style scoped></style>
