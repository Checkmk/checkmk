<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { CheckboxListChoice } from '@/form/components/vue_formspec_components'
import FormCheckboxListChoice from '@/form/components/forms/FormCheckboxListChoice.vue'

const spec: CheckboxListChoice = {
  type: 'checkbox_list_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  elements: [
    {
      name: 'some_name_1',
      title: 'some title 1'
    },
    {
      name: 'some_name_2',
      title: 'some title 2'
    }
  ]
}

const data = ref<Array<string>>(['some_name_1'])
</script>

<template>
  <pre>{{ JSON.stringify(data) }}</pre>
  <FormCheckboxListChoice v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
