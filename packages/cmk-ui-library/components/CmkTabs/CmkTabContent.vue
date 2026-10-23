<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsContent } from 'reka-ui'

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
  padding: var(--dimension-5);
  background: var(--background-subtle);
  border-top: 1px solid var(--border-color-strong);
  border-radius: 0 var(--dimension-3) var(--dimension-3);

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
