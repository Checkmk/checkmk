<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Integer } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import FormInteger from '@/form/private/forms/FormInteger.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<Integer>({
  type: 'integer',
  label: 'some label',
  input_hint: 'some input hint',
  unit: '%',
  title: 'some title',
  help: 'some help',
  validators: []
})

const data = ref<number>(10)

const backendValidation = [
  { location: [], message: 'some backend validation', replacement_value: true }
]
</script>

<template>
  <FormInteger v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
</template>
