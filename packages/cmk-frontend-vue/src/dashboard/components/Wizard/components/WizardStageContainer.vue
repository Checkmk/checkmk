<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    overflowHidden?: boolean
  }>(),
  {
    overflowHidden: false
  }
)
</script>

<template>
  <div class="db-wizard-stage-container__steps-container">
    <div
      class="db-wizard-stage-container__steps-inner-container"
      :class="{ 'db-wizard-stage-container--overflow-hidden': props.overflowHidden }"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.db-wizard-stage-container__steps-container {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: var(--dimension-10);
  box-sizing: border-box;
  background-color: var(--ux-theme-1);
}

.db-wizard-stage-container__steps-inner-container {
  height: 95vh;
  max-height: 100%;
  overflow-y: auto;
  position: relative;
}

.db-wizard-stage-container__steps-inner-container.db-wizard-stage-container--overflow-hidden {
  overflow-y: hidden;
}
</style>
