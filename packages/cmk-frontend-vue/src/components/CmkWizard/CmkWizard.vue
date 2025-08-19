<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
export interface CmkWizardProps {
  mode: 'overview' | 'guided'
}

defineProps<CmkWizardProps>()
</script>

<template>
  <ol class="cmk-wizard">
    <slot />
  </ol>
</template>

<style scoped>
.cmk-wizard {
  margin: var(--dimension-4) 0 0;
  padding-left: 0;
  counter-reset: stage-index;
}
</style>
