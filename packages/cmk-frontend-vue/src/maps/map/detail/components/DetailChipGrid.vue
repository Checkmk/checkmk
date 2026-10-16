<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A row of per-state counts: how many of the things behind this object are
critical, warning, unknown, ok.

The drawer states this four times over -- a host's services, a group's members,
an aggregation's leaves -- so the shape lives here once. A chip that leads
somewhere is a link, a chip the caller listens to is a button, and a chip that
is only a number is neither.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export interface DetailChip {
  /** Stable key, and what a listener gets told was picked. */
  key: string
  label: string
  count: number
  tone: 'crit' | 'warn' | 'unknown' | 'pending' | 'ok'
  /** Where the chip leads, if it leads anywhere. */
  url?: string | null
}

const props = defineProps<{
  chips: DetailChip[]
  /** Heading above the row, where the counts need naming. */
  label?: TranslatedString | undefined
  /**
   * Whether picking a chip does anything. The aggregation summary states its
   * counts without offering an action, so its chips are plain text rather than
   * buttons that lead nowhere.
   */
  interactive?: boolean
}>()

const emit = defineEmits<{ pick: [chip: DetailChip] }>()

// A count of zero has nothing to lead to: linking it would offer the operator a
// view that is empty by construction.
function linkOf(chip: DetailChip): string | null {
  return chip.count > 0 ? (chip.url ?? null) : null
}

function elementOf(chip: DetailChip): 'a' | 'button' | 'span' {
  if (linkOf(chip)) {
    return 'a'
  }
  return props.interactive ? 'button' : 'span'
}
</script>

<template>
  <div v-if="chips.length">
    <div v-if="label" class="maps-detail-chip-grid__label">{{ label }}</div>
    <div
      class="maps-detail-chip-grid"
      :style="{ gridTemplateColumns: `repeat(${chips.length}, 1fr)` }"
    >
      <component
        :is="elementOf(chip)"
        v-for="chip in chips"
        :key="chip.key"
        :href="linkOf(chip) || undefined"
        :target="linkOf(chip) ? '_blank' : undefined"
        :rel="linkOf(chip) ? 'noopener noreferrer' : undefined"
        :type="elementOf(chip) === 'button' ? 'button' : undefined"
        class="maps-detail-chip-grid__chip"
        :class="
          chip.count > 0
            ? `maps-detail-chip-grid__chip--${chip.tone}`
            : 'maps-detail-chip-grid__chip--zero'
        "
        @click="emit('pick', chip)"
      >
        <span class="maps-detail-chip-grid__count">{{ chip.count }}</span>
        <span class="maps-detail-chip-grid__chip-label">{{ chip.label }}</span>
      </component>
    </div>
  </div>
</template>

<style scoped>
.maps-detail-chip-grid {
  /* Column count comes from the chip count: the row always fills its width. */
  display: grid;
  gap: var(--dimension-4);
}

.maps-detail-chip-grid__label {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-4);
}

.maps-detail-chip-grid__chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-1);
  padding: var(--dimension-4) var(--dimension-3);
  border-radius: var(--border-radius);
  border: 1px solid var(--default-border-color);
  background: var(--ux-theme-1);
  color: var(--font-color);
  font: inherit;
  text-decoration: none;
  transition:
    transform 0.1s ease,
    border-color 0.1s ease;
}

a.maps-detail-chip-grid__chip,
button.maps-detail-chip-grid__chip {
  cursor: pointer;
}

a.maps-detail-chip-grid__chip:hover,
button.maps-detail-chip-grid__chip:hover {
  transform: translateY(-1px);
}

.maps-detail-chip-grid__count {
  font-size: var(--font-size-xlarge);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.maps-detail-chip-grid__chip-label {
  font-size: var(--font-size-small);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-medium);
}

/* Tinted like Checkmk's own status surfaces, with the matching text ink, so a
   chip and the object it counts read as the same state. */
.maps-detail-chip-grid__chip--crit {
  background: color-mix(in srgb, var(--color-state-critical) var(--status-tint-mix), transparent);
  border-color: color-mix(
    in srgb,
    var(--color-state-critical) var(--status-tint-border-mix),
    transparent
  );
}

.maps-detail-chip-grid__chip--crit .maps-detail-chip-grid__count,
.maps-detail-chip-grid__chip--crit .maps-detail-chip-grid__chip-label {
  color: var(--status-text-color-error-on-tint);
}

.maps-detail-chip-grid__chip--warn {
  background: color-mix(in srgb, var(--color-state-warning) var(--status-tint-mix), transparent);
  border-color: color-mix(
    in srgb,
    var(--color-state-warning) var(--status-tint-border-mix),
    transparent
  );
}

.maps-detail-chip-grid__chip--warn .maps-detail-chip-grid__count,
.maps-detail-chip-grid__chip--warn .maps-detail-chip-grid__chip-label {
  color: var(--status-text-color-warning-strong);
}

.maps-detail-chip-grid__chip--unknown {
  background: color-mix(in srgb, var(--color-state-unknown) var(--status-tint-mix), transparent);
  border-color: color-mix(
    in srgb,
    var(--color-state-unknown) var(--status-tint-border-mix),
    transparent
  );
}

.maps-detail-chip-grid__chip--unknown .maps-detail-chip-grid__count,
.maps-detail-chip-grid__chip--unknown .maps-detail-chip-grid__chip-label {
  color: var(--status-text-color-unknown-on-tint);
}

.maps-detail-chip-grid__chip--pending {
  background: color-mix(in srgb, var(--color-state-pending) var(--status-tint-mix), transparent);
  border-color: color-mix(
    in srgb,
    var(--color-state-pending) var(--status-tint-border-mix),
    transparent
  );
}

.maps-detail-chip-grid__chip--pending .maps-detail-chip-grid__count,
.maps-detail-chip-grid__chip--pending .maps-detail-chip-grid__chip-label {
  color: var(--status-text-color-pending);
}

.maps-detail-chip-grid__chip--ok {
  background: color-mix(in srgb, var(--color-state-ok) var(--status-tint-mix), transparent);
  border-color: color-mix(
    in srgb,
    var(--color-state-ok) var(--status-tint-border-mix),
    transparent
  );
}

.maps-detail-chip-grid__chip--ok .maps-detail-chip-grid__count,
.maps-detail-chip-grid__chip--ok .maps-detail-chip-grid__chip-label {
  color: var(--status-text-color-success-on-tint);
}

.maps-detail-chip-grid__chip--zero {
  opacity: 0.45;
}
</style>
