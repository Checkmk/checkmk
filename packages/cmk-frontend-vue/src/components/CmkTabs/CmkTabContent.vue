<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsContent } from 'radix-vue'

export interface CmkTabContentProps {
  id: string
  spacing?: 'default' | 'none'
}

defineProps<CmkTabContentProps>()
</script>

<template>
  <TabsContent :value="id" class="cmk-tab-content" :class="{ 'spacing-none': spacing === 'none' }">
    <slot />
  </TabsContent>
</template>

<style scoped>
.cmk-tab-content {
  margin-top: -1px;
  padding: var(--spacing);
  border: 1px solid var(--ux-theme-7);

  &:focus-visible {
    outline: none;
    border: 1px solid var(--success);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.spacing-none {
    padding: 0;
  }
}
</style>
