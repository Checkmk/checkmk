<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Host names the slide-in mentions. One that is also on this map can be selected
there -- following a dependency on the map is usually what the operator wanted;
the rest are names.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import { computed } from 'vue'

const props = defineProps<{
  hosts: readonly string[]
  /** Host names on this map, which a chip can therefore lead to. */
  selectableHosts: readonly string[]
}>()

const emit = defineEmits<{ 'select-host': [hostName: string] }>()

const selectable = computed(() => new Set(props.selectableHosts))
</script>

<template>
  <span class="maps-detail-host-chips">
    <CmkChip
      v-for="host in hosts"
      :key="host"
      size="small"
      color="info"
      variant="outline"
      :as-div="!selectable.has(host)"
      @click="selectable.has(host) ? emit('select-host', host) : undefined"
    >
      {{ host }}
    </CmkChip>
  </span>
</template>

<style scoped>
.maps-detail-host-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
}
</style>
