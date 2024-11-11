<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as typing from '@/form/components/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'

defineProps<{
  spec: typing.ConditionChoices
  backendValidation: ValidationMessages
}>()

const data = defineModel<typing.ConditionChoicesValue[]>('data', { required: true })
</script>

<template>
  <pre>{{ data }}</pre>
</template>
