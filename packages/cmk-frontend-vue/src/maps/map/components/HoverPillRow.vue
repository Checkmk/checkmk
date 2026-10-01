<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One labelled row of state counts on a hover card -- "SERVICES 1 WARN 1 OK".
-->
<script setup lang="ts">
export type PillTone = 'crit' | 'unknown' | 'warn' | 'pending' | 'ok'

export interface HoverPill {
  label: string
  count: number
  tone: PillTone
  /** Deep-link into the filtered Checkmk view, or null when not linkable. */
  url: string | null
}

defineProps<{
  label: string
  pills: HoverPill[]
}>()
</script>

<template>
  <div class="maps-hover-pill-row">
    <span class="maps-hover-pill-row__label">{{ label }}</span>
    <component
      :is="pill.url ? 'a' : 'span'"
      v-for="pill in pills"
      :key="pill.label"
      class="maps-hover-pill-row__pill"
      :class="[
        `maps-hover-pill-row__pill--${pill.tone}`,
        { 'maps-hover-pill-row__pill--link': pill.url }
      ]"
      :href="pill.url || undefined"
      :target="pill.url ? '_blank' : undefined"
      :rel="pill.url ? 'noopener noreferrer' : undefined"
    >
      <span
        class="maps-hover-pill-row__pill-dot"
        :class="`maps-hover-pill-row__pill-dot--${pill.tone}`"
      />
      {{ pill.count }} {{ pill.label }}
    </component>
  </div>
</template>

<style scoped>
.maps-hover-pill-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3);
  margin-top: var(--spacing);
}

.maps-hover-pill-row__label {
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--font-color-dimmed);
  margin-right: var(--dimension-2);
}

.maps-hover-pill-row__pill {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  border-radius: 9999px;
}

.maps-hover-pill-row__pill--link {
  cursor: pointer;
  text-decoration: none;

  &:hover {
    filter: brightness(1.25);
    text-decoration: underline;
  }
}

.maps-hover-pill-row__pill--crit {
  color: var(--color-light-red-70);
  background: color-mix(in srgb, var(--color-light-red-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-pill-row__pill--crit {
  color: var(--color-light-red-40);
}

.maps-hover-pill-row__pill--unknown {
  color: var(--color-orange-70);
  background: color-mix(in srgb, var(--color-orange-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-orange-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-pill-row__pill--unknown {
  color: var(--color-orange-40);
}

.maps-hover-pill-row__pill--warn {
  color: var(--color-yellow-60);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-pill-row__pill--warn {
  color: var(--color-yellow-50);
}

.maps-hover-pill-row__pill--pending {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--color-state-pending) 15%, transparent);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-hover-pill-row__pill--ok {
  color: var(--color-corporate-green-70);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

body[data-theme='modern-dark'] .maps-hover-pill-row__pill--ok {
  color: var(--color-corporate-green-50);
}

.maps-hover-pill-row__pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.maps-hover-pill-row__pill-dot--crit {
  background: var(--color-light-red-50);
}

.maps-hover-pill-row__pill-dot--unknown {
  background: var(--color-orange-40);
}

.maps-hover-pill-row__pill-dot--warn {
  background: var(--color-warning);
}

.maps-hover-pill-row__pill-dot--pending {
  background: var(--color-state-pending);
}

.maps-hover-pill-row__pill-dot--ok {
  background: var(--color-corporate-green-50);
}
</style>
