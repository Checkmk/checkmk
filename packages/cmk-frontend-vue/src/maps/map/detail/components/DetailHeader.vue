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
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectState } from '@/maps/types/api'
import { stateColorVar } from '@/maps/utils/stateColors'

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

const statePillStyle = computed(() => {
  const color = stateColorVar(props.state?.state)
  // The border follows the text through `currentcolor`; only the tint has to
  // be mixed here, since CSS cannot tint a colour it is only given at runtime.
  return { color, background: `color-mix(in srgb, ${color} 12%, transparent)` }
})
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
          :title="name"
          :aria-label="_t('Open in Checkmk')"
          >{{ name }}</a
        >
        <span v-else class="maps-detail-header__name" :title="name">{{ name }}</span>
        <span class="maps-detail-header__type-pill">{{ typeLabel }}</span>
      </h2>
      <div v-if="state" class="maps-detail-header__state-line">
        <!-- Live: the state changes under the reader while the drawer is open. -->
        <span
          class="maps-detail-header__state-pill"
          role="status"
          :aria-label="_t('Current state')"
          :style="statePillStyle"
        >
          {{ state.state }}
        </span>
        <span v-if="since" class="maps-detail-header__since">{{ since }}</span>
      </div>
    </div>

    <a
      v-if="checkmkUrl"
      :href="checkmkUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="maps-detail-header__icon-btn"
      :title="_t('Open in Checkmk')"
      :aria-label="_t('Open in Checkmk')"
    >
      <CmkIcon name="export-link" size="small" />
    </a>
    <a
      v-if="setupUrl"
      :href="setupUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="maps-detail-header__icon-btn"
      :title="_t('Edit in Checkmk Setup')"
      :aria-label="_t('Edit in Checkmk Setup')"
    >
      <CmkIcon name="main-setup" size="small" />
    </a>
    <button
      type="button"
      class="maps-detail-header__icon-btn maps-detail-header__icon-btn--close"
      :title="_t('Close')"
      :aria-label="_t('Close')"
      @click="emit('close')"
    >
      <span aria-hidden="true">{{ untranslated('×') }}</span>
    </button>
  </header>
</template>

<style scoped>
.maps-detail-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing);
  padding: 12px 16px;
  border-bottom: 1px solid var(--default-border-color);
  flex-shrink: 0;
}

.maps-detail-header__title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  font-weight: var(--font-weight-bold);
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
  color: var(--color-corporate-green-50);
  text-decoration: underline;
}

.maps-detail-header__type-pill {
  color: var(--font-color-dimmed);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: 999px;
  padding: 1px 6px;
  flex-shrink: 0;
  font-weight: var(--font-weight-bold);
}

.maps-detail-header__state-line {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex-wrap: wrap;
}

.maps-detail-header__state-pill {
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.04em;
  padding: 2px 10px;
  border: 1px solid currentcolor;
  border-radius: 999px;
}

.maps-detail-header__since {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-detail-header__icon-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--input-hover-bg-color);
  color: var(--font-color);
  border: none;
  cursor: pointer;
  font-size: var(--font-size-xxlarge);
  line-height: 22px;
  text-align: center;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  flex-shrink: 0;
}

.maps-detail-header__icon-btn--close {
  color: var(--font-color-dimmed);
}

.maps-detail-header__icon-btn:hover {
  color: var(--color-corporate-green-50);
  background: var(--ux-theme-1);
}
</style>
