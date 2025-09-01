<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n.ts'

import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

const { _t } = usei18n()
const currentMode = defineModel<string>({ required: true })
</script>

<template>
  <ToggleButtonGroup
    v-model="currentMode"
    :options="[
      { label: _t('Guided'), value: 'guided' },
      { label: _t('Overview'), value: 'overview' }
    ]"
  />
</template>
