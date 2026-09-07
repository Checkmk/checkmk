<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'

import type { CommandChoice } from '../lib/types'

defineProps<{ choices: CommandChoice[] }>()

const selected = defineModel<string>({ required: true })
</script>

<template>
  <CmkToggleButtonGroup
    v-if="choices.length > 1"
    v-model="selected"
    class="mh-shell-toggle"
    :options="choices.map((choice) => ({ label: choice.label, value: choice.id }))"
  />
</template>

<style scoped>
.mh-shell-toggle {
  margin-top: var(--dimension-5);
  margin-bottom: var(--dimension-5);
}
</style>
