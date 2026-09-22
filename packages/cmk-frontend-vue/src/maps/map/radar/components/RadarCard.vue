<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One monitored thing on a radar map: its name, its state, and what somebody has
already done about it.

The card is tinted by its own state, so a wall of them reads as a status at a
glance. That tint is one custom property the state resolves to, so the card's
frame, ink and background all follow the one shared monitoring-state token.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectState } from '@/maps/types/api'
import { stateAriaLabel } from '@/maps/utils/objectAria'
import { stateColorVar } from '@/maps/utils/stateColors'

import MapStateTag from './MapStateTag.vue'

const props = defineProps<{
  state: ObjectState
  /** What the card is called: a service is named under its host. */
  name: string
  /**
   * The settings preview, which shows a shrunk-down sample of the map. There is
   * nothing to open from it, so the card is neither clickable nor focusable.
   */
  compact: boolean
}>()

const emit = defineEmits<{ activate: [event?: MouseEvent] }>()

const { _t } = usei18n()

const tint = computed(() => ({ '--maps-radar-card-color': stateColorVar(props.state.state) }))

function onClick(event: MouseEvent): void {
  if (!props.compact) {
    emit('activate', event)
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (props.compact || (event.key !== 'Enter' && event.key !== ' ')) {
    return
  }
  event.preventDefault()
  emit('activate')
}
</script>

<template>
  <div
    class="maps-radar-card"
    :class="{ 'maps-radar-card--compact': compact }"
    :style="tint"
    :tabindex="compact ? -1 : 0"
    :role="compact ? undefined : 'button'"
    :aria-label="`${name}, ${stateAriaLabel(_t, state.state)}`"
    @click="onClick"
    @keydown="onKeydown"
  >
    <div class="maps-radar-card__head">
      <span class="maps-radar-card__name">{{ name }}</span>
      <div v-if="!compact" class="maps-radar-card__flags">
        <CmkIcon
          v-if="state.acknowledged"
          name="checkmark"
          size="small"
          :title="_t('Acknowledged')"
        />
        <CmkIcon v-if="state.in_downtime" name="downtime" size="small" :title="_t('In downtime')" />
      </div>
    </div>

    <MapStateTag
      :state="state.state"
      :kind="state.type === 'service' ? 'service' : 'host'"
      :size="compact ? 'inline' : 'default'"
      :stale="state.stale"
    />

    <p v-if="state.output && !compact" class="maps-radar-card__output">{{ state.output }}</p>
  </div>
</template>

<style scoped>
.maps-radar-card {
  padding: 14px;

  /* The state colours are background colours, too dark to read as ink in the
     dark theme; mixed towards the theme's font colour they keep the state's
     hue and stay legible in both themes. */
  color: color-mix(in srgb, var(--maps-radar-card-color) 65%, var(--font-color));
  background: color-mix(in srgb, var(--maps-radar-card-color) 8%, transparent);
  border-radius: 12px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--maps-radar-card-color) 20%, transparent);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-radar-card:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-radar-card:not(.maps-radar-card--compact):hover {
  transform: translateY(-2px);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--maps-radar-card-color) 20%, transparent),
    var(--maps-map-view-badge-shadow);
}

.maps-radar-card--compact {
  padding: var(--dimension-4);
  cursor: default;
}

.maps-radar-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-4);
}

.maps-radar-card__name {
  font-family: monospace;
  font-size: var(--font-size-normal);
  line-height: 1.25;
  font-weight: var(--font-weight-bold);

  /* A host or service name with no spaces still has to wrap rather than
     overflow the card, but only where it does not fit -- break-all split every
     line mid-word ("Check_MK Discove / ry"). */
  overflow-wrap: anywhere;
}

.maps-radar-card--compact .maps-radar-card__name {
  font-size: var(--font-size-small);
}

.maps-radar-card__flags {
  display: flex;
  flex-shrink: 0;
  gap: var(--dimension-3);
  opacity: 0.7;
}

.maps-radar-card__output {
  overflow: hidden;
  display: -webkit-box;
  margin-top: var(--dimension-4);

  /* Dimming the state's own ink far enough to read as secondary would leave it
     illegible on the tinted card. */
  color: var(--font-color-dimmed);
  font-size: 11px;
  line-height: 1.375;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
