<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TabsTrigger } from 'radix-vue'

export interface CmkTabProps {
  id: string
  disabled?: boolean | undefined
}

defineProps<CmkTabProps>()
</script>

<template>
  <TabsTrigger :value="id" :disabled="!!disabled" as="li" class="cmk-tab-li">
    <slot />
  </TabsTrigger>
</template>

<style scoped>
.cmk-tab-li {
  display: flex;
  flex-direction: row;
  background: var(--ux-theme-0);
  padding: 10px 16px 8px 16px;

  &:hover {
    cursor: pointer;
    background: var(--ux-theme-2);
  }

  &:focus,
  &:active {
    outline-width: 1px;
    outline-color: var(--success);
  }

  &[data-state='active'] {
    background: var(--ux-theme-3);
  }
  &[data-disabled] {
    opacity: 0.6;
    cursor: default;
    background: var(--ux-theme-0);
  }

  &[data-orientation='vertical'] {
    padding: 8px 16px 8px 18px;
  }
}
</style>
