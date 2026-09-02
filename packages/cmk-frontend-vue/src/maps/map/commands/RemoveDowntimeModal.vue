<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { DowntimeEntry } from '@/maps/types/api'

const { commands } = useMapsApis()

const props = defineProps<{
  downtimes: DowntimeEntry[]
  checkmkUrl: string
  objectName: string
}>()

const emit = defineEmits<{ close: [] }>()

const { _t, _tn } = usei18n()
const removingId = ref<string | null>(null)
const error = ref('')

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function remove(dt: DowntimeEntry) {
  if (removingId.value !== null) {
    return
  }
  removingId.value = dt.id
  error.value = ''
  try {
    await commands.removeDowntimeById(props.checkmkUrl, dt.id, dt.site_id)
    emit('close')
  } catch (e) {
    error.value = e instanceof Error ? e.message : _t('Failed to remove downtime')
    removingId.value = null
  }
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Remove downtime')" closable @close="$emit('close')">
    <p class="maps-remove-downtime-modal__subtitle">
      {{ objectName }} &mdash;
      {{
        downtimes.length === 0
          ? _t('no active downtimes')
          : _tn('%{n} downtime active', '%{n} downtimes active', downtimes.length, {
              n: downtimes.length
            })
      }}
    </p>

    <CmkScrollContainer max-height="224px" height="auto">
      <div class="maps-remove-downtime-modal__list">
        <div v-for="dt in downtimes" :key="dt.id" class="maps-remove-downtime-modal__item">
          <div class="maps-remove-downtime-modal__meta">
            <p class="maps-remove-downtime-modal__author">
              {{ dt.author }}<span v-if="dt.comment"> &bull; {{ dt.comment }}</span>
            </p>
            <p class="maps-remove-downtime-modal__period">
              {{ formatTime(dt.start_time) }} &ndash; {{ formatTime(dt.end_time) }}
            </p>
          </div>
          <CmkButton variant="danger" :disabled="removingId !== null" @click="remove(dt)">
            {{ removingId === dt.id ? _t('Removing…') : _t('Remove') }}
          </CmkButton>
        </div>
      </div>
    </CmkScrollContainer>

    <CmkAlertBox v-if="error" variant="error" size="small">{{ error }}</CmkAlertBox>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-remove-downtime-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
}

.maps-remove-downtime-modal__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--dimension-5);
  padding: var(--dimension-4) 0;
}

.maps-remove-downtime-modal__list
  > .maps-remove-downtime-modal__item
  + .maps-remove-downtime-modal__item {
  border-top: 1px solid var(--default-border-color);
}

.maps-remove-downtime-modal__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.maps-remove-downtime-modal__author {
  font-size: var(--font-size-large);
  font-weight: 500;
  color: var(--font-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-remove-downtime-modal__period {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}
</style>
