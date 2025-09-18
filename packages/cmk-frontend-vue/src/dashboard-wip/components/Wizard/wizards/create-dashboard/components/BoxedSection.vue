<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

interface BoxedSectionProps {
  displayBorder?: boolean
}

const props = defineProps<BoxedSectionProps>()

const borderStyle = computed(() => {
  return props.displayBorder ? '1px solid var(--color-corporate-green-50)' : 'none'
})
</script>

<template>
  <div class="db-boxed-section__root">
    <div class="db-boxed-section__item">
      <slot name="header" />
    </div>
    <div class="db-boxed-section__item">
      <slot name="content" />
    </div>
  </div>
</template>

<style scoped>
.db-boxed-section__root {
  display: flex;
  flex-direction: column;
  width: 100%;
  background: var(--ux-theme-2);
  border: v-bind(borderStyle);
}

.db-boxed-section__item {
  display: flex;
  flex-direction: column;
  border: 1px solid transparent;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
  padding: 10px;

  &:first-of-type {
    border-bottom: v-bind(borderStyle);
    background: var(--ux-theme-4);
  }

  &:last-of-type {
    margin-bottom: 0;
  }
}
</style>
