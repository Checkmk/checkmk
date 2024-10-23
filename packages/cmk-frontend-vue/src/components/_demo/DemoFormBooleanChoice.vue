<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
import type { BooleanChoice } from '@/form/components/vue_formspec_components'
import FormBooleanChoice from '@/form/components/forms/FormBooleanChoice.vue'
const spec = ref<BooleanChoice>({
  type: 'boolean_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  label: 'some label',
  text_off: 'some text off',
  text_on: 'some text on'
})
const data = ref<boolean>(true)
</script>

<template>
  <FormBooleanChoice v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
