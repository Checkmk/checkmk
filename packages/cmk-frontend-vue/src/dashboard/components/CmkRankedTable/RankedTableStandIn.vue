<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'

const {
  animated,
  shape = 'text',
  width = '100%'
} = defineProps<{
  animated: boolean
  /** `track` stands in for a bar track and takes the remaining width. */
  shape?: 'text' | 'track'
  width?: string
}>()
</script>

<template>
  <span v-if="shape === 'track'" class="db-ranked-table-stand-in__track">
    <CmkSkeleton v-if="animated" type="box" />
  </span>
  <CmkSkeleton v-else-if="animated" class="db-ranked-table-stand-in" type="text" :width="width" />
  <span v-else class="db-ranked-table-stand-in db-ranked-table-stand-in--static" />
</template>

<style scoped>
.db-ranked-table-stand-in {
  display: block;
  max-width: 100%;
}

.db-ranked-table-stand-in--static {
  width: v-bind(width);
  height: var(--font-size-normal);
  background-color: var(--color-skeleton);
  border-radius: var(--border-radius);
}

.db-ranked-table-stand-in__track {
  display: block;
  flex: 1;
  min-width: 4em;
  height: var(--dimension-3);
  overflow: hidden;
  background-color: var(--color-skeleton);
  border-radius: 99999px;
}
</style>
