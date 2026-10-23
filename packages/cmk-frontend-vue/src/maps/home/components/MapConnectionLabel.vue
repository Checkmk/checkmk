<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Which Livestatus connection a listed map runs against, by its display name
("cmk ZWEIFUENF") rather than its id — the id is the title, for the case where
two connections are named alike. Administration, so only an administrator sees
it; the card and the table show it the same way.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'

import { useConnections } from '@/maps/services/context'

const props = defineProps<{ connectionId: string }>()

const connections = useConnections()
</script>

<template>
  <span class="maps-map-connection-label" :title="props.connectionId">
    <CmkIcon name="sites" size="xsmall" :colored="false" />
    <span class="maps-map-connection-label__name">
      {{ connections.labelFor(props.connectionId) }}
    </span>
  </span>
</template>

<style scoped>
.maps-map-connection-label {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  min-width: 0;
}

/* No typeface or colour of its own: this reads inside a line of plain facts, and
   the exact id - the reason a monospace would earn its place - is the title. */
.maps-map-connection-label__name {
  overflow: hidden;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
