<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import { required } from './requiredValidator'

const { spec, space = null } = defineProps<{
  spec?: FormSpec
  space?: ('before' | 'after' | 'both') | null
}>()
</script>

<template>
  <CmkLabelRequired
    :show="spec?.validators?.some(required) ?? false"
    :style="{ padding: '3px 0' }"
    :space="space"
  />
</template>
