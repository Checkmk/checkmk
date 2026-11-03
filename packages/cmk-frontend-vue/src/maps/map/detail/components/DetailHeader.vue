<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Who this drawer is about and what state they are in.

The name links into Checkmk, because the drawer is a summary and Checkmk is the
full record. An aggregation additionally links into Setup: when its behaviour
needs adjusting, the BI pack is where that happens.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapStateTag from '@/maps/map/radar/components/MapStateTag.vue'
import type { ObjectState } from '@/maps/types/api'

const props = defineProps<{
  name: string
  /** The object's kind, spelled out ("Service", "Host group"). */
  typeLabel: string
  state: ObjectState | undefined
  /** How long the object has been in this state, where that is known. */
  since: string | null
  /** The object in Checkmk's own views. */
  checkmkUrl: string | null
  /** An aggregation's BI pack in Setup. */
  setupUrl?: string | null
}>()

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()

const openTitle = computed(() => _t('Open the state of %{name} in a new tab', { name: props.name }))
</script>

<template>
  <header class="maps-detail-header">
    <div class="maps-detail-header__title">
      <!-- The object's name is the drawer's heading: it is what the whole
           slide-in is about, and a reader arriving in it needs it announced. -->
      <h2 class="maps-detail-header__title-row">
        <a
          v-if="checkmkUrl"
          :href="checkmkUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="maps-detail-header__name maps-detail-header__name--link"
          :title="openTitle"
          :aria-label="openTitle"
          >{{ name }}</a
        >
        <span v-else class="maps-detail-header__name" :title="name">{{ name }}</span>
        <span class="maps-detail-header__type-pill">{{ typeLabel }}</span>
      </h2>
      <div v-if="state" class="maps-detail-header__state-line">
        <!-- Live: the state changes under the reader while the drawer is open. -->
        <span role="status" :aria-label="_t('Current state')">
          <MapStateTag
            :state="state.state"
            :kind="state.type === 'service' ? 'service' : 'host'"
            :stale="state.stale"
          />
        </span>
        <span v-if="since" class="maps-detail-header__since">{{ since }}</span>
      </div>
    </div>

    <div class="maps-detail-header__actions">
      <CmkIconLink
        v-if="checkmkUrl"
        name="export-link"
        size="small"
        :href="checkmkUrl"
        target="_blank"
        rel="noopener noreferrer"
        :title="openTitle"
        :aria-label="openTitle"
      />
      <CmkIconLink
        v-if="setupUrl"
        name="main-setup"
        size="small"
        :href="setupUrl"
        target="_blank"
        rel="noopener noreferrer"
        :title="_t('Edit in Checkmk Setup')"
        :aria-label="_t('Edit in Checkmk Setup')"
      />
      <CmkIconButton
        name="close"
        size="xsmall"
        :title="_t('Close')"
        :aria-label="_t('Close')"
        @click="emit('close')"
      />
    </div>
  </header>
</template>

<style scoped>
.maps-detail-header {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-5);
  padding: var(--dimension-5) var(--dimension-6);
  border-bottom: 1px solid var(--default-border-color);
  flex-shrink: 0;
}

.maps-detail-header__title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-detail-header__title-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  min-width: 0;

  /* A heading for the reader, not for the eye: the name carries its own size. */
  margin: 0;
  font-size: inherit;
  font-weight: inherit;
}

.maps-detail-header__name {
  font-weight: var(--font-weight-medium);
  color: var(--font-color);
  font-size: var(--font-size-large);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.maps-detail-header__name--link {
  cursor: pointer;
  text-decoration: none;
}

.maps-detail-header__name--link:hover,
.maps-detail-header__name--link:focus-visible {
  color: var(--interactive-accent);
  text-decoration: underline;
}

.maps-detail-header__type-pill {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: 999px;
  padding: var(--dimension-1) var(--dimension-4);
  flex-shrink: 0;
  font-weight: var(--font-weight-medium);
}

.maps-detail-header__state-line {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex-wrap: wrap;
}

.maps-detail-header__since {
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.maps-detail-header__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex-shrink: 0;
}
</style>
