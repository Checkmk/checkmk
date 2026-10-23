<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a command that goes out to many things is about to be sent about.

Shown before it is sent, because there is no undo: fanning a command out over
the wrong selection cannot be taken back in one go.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { describeTarget, targetKey } from '@/maps/map/commands/fanOutCommand'
import type { CommandTarget } from '@/maps/types/api'

/** Enough to see what this is about; a selection can run to hundreds. */
const MAX_VISIBLE = 20

const { _t } = usei18n()

const props = defineProps<{ targets: CommandTarget[] }>()

const visible = computed(() => props.targets.slice(0, MAX_VISIBLE))
const hidden = computed(() => Math.max(0, props.targets.length - MAX_VISIBLE))
</script>

<template>
  <ul class="maps-command-target-list">
    <li
      v-for="target in visible"
      :key="targetKey(target)"
      class="maps-command-target-list__item"
      :title="describeTarget(target)"
    >
      {{ target.host
      }}<span v-if="target.service" class="maps-command-target-list__service">
        / {{ target.service }}</span
      >
    </li>
    <li v-if="hidden > 0" class="maps-command-target-list__item">
      <span class="maps-command-target-list__service">
        {{ _t('and %{count} more', { count: hidden }) }}
      </span>
    </li>
  </ul>
</template>

<style scoped>
.maps-command-target-list {
  max-height: 160px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  font-size: var(--font-size-normal);
  list-style: none;
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
}

.maps-command-target-list__item {
  padding: var(--dimension-3) var(--dimension-5);
  overflow: hidden;
  color: var(--font-color);
  font-family: monospace;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.maps-command-target-list > .maps-command-target-list__item + .maps-command-target-list__item {
  border-top: 1px solid var(--default-border-color);
}

.maps-command-target-list__service {
  color: var(--font-color-dimmed);
}
</style>
