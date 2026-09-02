<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Deleting a selection from the table view. It is the same confirmation the single
delete asks for, plus the list of what is about to go.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'

const MAX_VISIBLE = 20

const props = defineProps<{ open: boolean; names: string[]; busy?: boolean }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()

const { _t } = usei18n()
const shown = computed(() => props.names.slice(0, MAX_VISIBLE))
const overflow = computed(() => Math.max(0, props.names.length - MAX_VISIBLE))
</script>

<template>
  <MapsConfirmDialog
    :open="open"
    variant="error"
    :title="_t('Delete %{n} maps', { n: names.length })"
    :message="_t('The following maps will be permanently removed. This action cannot be undone.')"
    :confirm-label="_t('Delete')"
    :busy="busy"
    @confirm="emit('confirm')"
    @cancel="emit('cancel')"
  >
    <div class="maps-map-bulk-delete-dialog__names">
      <ul class="maps-map-bulk-delete-dialog__list">
        <li v-for="entry in shown" :key="entry">{{ entry }}</li>
      </ul>
      <p v-if="overflow > 0" class="maps-map-bulk-delete-dialog__more">
        {{ _t('… and %{n} more', { n: overflow }) }}
      </p>
    </div>
  </MapsConfirmDialog>
</template>

<style scoped>
.maps-map-bulk-delete-dialog__names {
  margin-bottom: var(--dimension-6);
}

.maps-map-bulk-delete-dialog__list {
  width: 380px;
  max-width: 100%;
  margin: 0;
  padding: var(--dimension-3) var(--dimension-5);
  list-style: disc inside;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius-half);
  font-family: var(--font-family-monospace, monospace);
  font-size: 0.9em;
  text-align: left;
}

.maps-map-bulk-delete-dialog__list li {
  padding: 1px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-map-bulk-delete-dialog__more {
  margin: var(--dimension-3) 0 0;
  color: var(--font-color-dimmed);
  font-style: italic;
  font-size: 0.9em;
}
</style>
