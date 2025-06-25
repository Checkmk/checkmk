<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsContent } from 'radix-vue'

export interface CmkTabContentProps {
  id: string
}

defineProps<CmkTabContentProps>()
</script>

<template>
  <TabsContent :value="id" class="cmk-tab-content">
    <slot />
  </TabsContent>
</template>

<style scoped>
.cmk-tab-content {
  padding: 16px;
  background: var(--ux-theme-3);

  &:focus,
  &:active {
    outline-width: 1px;
    outline-color: var(--success);
  }
}
</style>
