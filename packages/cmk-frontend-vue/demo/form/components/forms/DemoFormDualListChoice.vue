<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  DualListChoice,
  DualListChoiceI18N,
  MultipleChoiceElement
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import { type DualListElement } from '@/components/CmkDualList/index.ts'

import FormDualListChoice from '@/form/components/forms/FormDualListChoice.vue'

defineProps<{ screenshotMode: boolean }>()

// i18n isn't used anymore
const spec = ref<DualListChoice>({
  elements: [
    { name: 'Test_name_1', title: 'Test Name 1' },
    { name: 'Test_name_2', title: 'Test Name 2' },
    { name: 'Test_name_3', title: 'Test Name 3' },
    { name: 'Test_name_4', title: 'Test Name 4' }
  ] as MultipleChoiceElement[],
  show_toggle_all: true,

  type: 'dual_list_choice',
  title: 'the Title',
  help: '',
  validators: [],
  i18n: {
    add: '',
    remove: '',
    add_all: '',
    remove_all: '',
    available_options: '',
    selected_options: '',
    selected: '',
    no_elements_available: '',
    no_elements_selected: '',
    autocompleter_loading: '',
    search_available_options: '',
    search_selected_options: '',
    and_x_more: ''
  } as DualListChoiceI18N
})

const data = ref<DualListElement[]>([])
</script>

<template>
  <h2>Demo: Form Dual List Choice</h2>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormDualListChoice v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
