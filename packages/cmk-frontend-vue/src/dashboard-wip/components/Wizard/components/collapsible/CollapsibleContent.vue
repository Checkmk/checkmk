<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCollapsible from '@/components/CmkCollapsible.vue'

interface CollapsibleContent {
  open: boolean
}

defineProps<CollapsibleContent>()
</script>

<template>
  <CmkCollapsible :open="open" class="db-collapsible-content">
    <div class="db-collapsible-content__inner">
      <slot />
    </div>
  </CmkCollapsible>
</template>

<style scoped>
.db-collapsible-content {
  background-color: var(--ux-theme-3);
}

.db-collapsible-content__inner {
  padding: 10px;
}
</style>
