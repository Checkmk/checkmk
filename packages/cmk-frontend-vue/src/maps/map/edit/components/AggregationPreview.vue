<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the picked BI aggregation would put on the map: how its leaves are spread
across the states, and the first few of them by name.

Deliberately a count plus a sample rather than the tree itself — a fully
expanded aggregation runs to hundreds of nodes, which would make every
keystroke in the field above re-render all of them.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import {
  crowdingWarning,
  leafSample,
  leafStateCounts,
  leavesBeyondSample,
  leavesOf
} from '@/maps/map/edit/aggregationPreviewFacts'
import type { AggregationNode } from '@/maps/types/api'

const props = defineProps<{
  tree: AggregationNode | null
  connectionOk: boolean
  aggregationId: string
  expandDepth: number
}>()

const { _t } = usei18n()

const leaves = computed(() => leavesOf(props.tree))
const counts = computed(() => leafStateCounts(leaves.value))
const sample = computed(() => leafSample(leaves.value))
const beyondSample = computed(() => leavesBeyondSample(leaves.value))
const crowding = computed(() => crowdingWarning(leaves.value, props.expandDepth, _t))

// An unreachable connection must not read as "this aggregation has no leaves".
const unreachable = computed(() => !props.connectionOk && !!props.aggregationId && !props.tree)
</script>

<template>
  <CmkAlertBox v-if="unreachable" variant="warning">
    {{
      _t(
        'Preview unavailable — the Checkmk connection is unhealthy. Check the connection status and reload.'
      )
    }}
  </CmkAlertBox>
  <div v-else-if="tree" class="maps-aggregation-preview">
    <p class="maps-aggregation-preview__title">{{ _t('Preview (live state)') }}</p>
    <div class="maps-aggregation-preview__counts">
      <span
        v-for="count in counts"
        :key="count.key"
        class="maps-aggregation-preview__count"
        :style="{ color: count.count > 0 ? count.color : 'var(--font-color-dimmed)' }"
      >
        {{ count.label }}={{ count.count }}
      </span>
    </div>
    <ul class="maps-aggregation-preview__leaves">
      <li v-for="leaf in sample" :key="leaf.id" class="maps-aggregation-preview__leaf">
        <span class="maps-aggregation-preview__dot" :style="{ background: leaf.color }" />
        <span class="maps-aggregation-preview__leaf-name">{{ leaf.label }}</span>
      </li>
      <li v-if="beyondSample > 0" class="maps-aggregation-preview__more">
        {{ _t('…%{count} more', { count: beyondSample }) }}
      </li>
    </ul>
    <CmkAlertBox v-if="crowding" variant="warning">{{ crowding }}</CmkAlertBox>
  </div>
</template>

<style scoped>
.maps-aggregation-preview {
  padding: var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
}

.maps-aggregation-preview__title {
  margin: 0 0 var(--dimension-3);
  color: var(--font-color-dimmed);
}

.maps-aggregation-preview__counts {
  display: flex;
  gap: var(--dimension-5);
  margin-bottom: var(--dimension-3);
  font-family: monospace;
}

.maps-aggregation-preview__leaves {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.maps-aggregation-preview__leaf {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  color: var(--font-color);
}

.maps-aggregation-preview__dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: var(--border-radius-half);
}

.maps-aggregation-preview__leaf-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-aggregation-preview__more {
  font-style: italic;
  color: var(--font-color-dimmed);
}
</style>
