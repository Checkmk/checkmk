<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

import { makeString } from '@/graph-designer/private/specs'

const data = defineModel('data', { type: String, default: '' })
const spec = makeString('', '', null, 'LARGE')
const backendValidation: ValidationMessages = []
</script>

<template>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
</template>
