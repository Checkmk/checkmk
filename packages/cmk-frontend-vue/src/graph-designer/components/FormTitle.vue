<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormEdit from '@/form/components/FormEdit.vue'
import { type ValidationMessages } from '@/form'

const dataTitle = defineModel('dataTitle', { type: String, default: '' })
const specTitle = {
  type: 'string',
  title: '',
  help: '',
  validators: []
}
const backendValidationTitle: ValidationMessages = []
</script>
<template>
  <FormEdit
    v-model:data="dataTitle"
    :spec="specTitle"
    :backend-validation="backendValidationTitle"
  />
</template>
