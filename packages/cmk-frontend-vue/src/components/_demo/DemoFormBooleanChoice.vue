<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { BooleanChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormBooleanChoice from '@/form/components/forms/FormBooleanChoice.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<BooleanChoice>({
  type: 'boolean_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  label: 'some label',
  text_off: 'some text off',
  text_on: 'some text on'
})
const dataTrue = ref<boolean>(true)
const dataFalse = ref<boolean>(false)
</script>

<template>
  <h2>checked</h2>
  <FormBooleanChoice v-model:data="dataTrue" :spec="spec" :backend-validation="[]" />
  <code>&nbsp;{{ dataTrue }}</code>
  <h2>unchecked</h2>
  <FormBooleanChoice v-model:data="dataFalse" :spec="spec" :backend-validation="[]" />
  <code>&nbsp;{{ dataFalse }}</code>
</template>
