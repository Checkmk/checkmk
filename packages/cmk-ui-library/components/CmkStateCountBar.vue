<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkColorSwatch from 'cmk-ui-library/components/CmkColorSwatch.vue'
import type { Colors } from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

export interface StateSegment {
  label: TranslatedString
  count: number
  color: Colors | 'pending'
  href?: string | undefined
  target?: string | undefined
}

export interface StateTotal {
  label: TranslatedString
  href?: string | undefined
  target?: string | undefined
}

interface LegendEntry {
  label: TranslatedString
  count: number
  color: StateSegment['color']
  href: string | undefined
  target: string | undefined
}

/** `small` thins the bar where a list repeats one per row. */
export type StateCountBarSize = 'small' | 'medium'

const props = withDefaults(
  defineProps<{
    segments: StateSegment[]
    total?: StateTotal | undefined
    size?: StateCountBarSize
  }>(),
  { total: undefined, size: 'medium' }
)

const slots = defineSlots<{
  heading?: () => unknown
}>()

const { _t } = usei18n()

const totalCount = computed(() => props.segments.reduce((sum, segment) => sum + segment.count, 0))

/** Only non-zero segments occupy space in the bar; the legend still lists all of them. */
const barSegments = computed(() => props.segments.filter((segment) => segment.count > 0))

function toEntry(
  label: TranslatedString,
  count: number,
  color: StateSegment['color'],
  link: Pick<StateSegment, 'href' | 'target'>
): LegendEntry {
  return {
    label,
    count,
    color,
    href: count > 0 ? link.href : undefined,
    target: count > 0 ? link.target : undefined
  }
}

const legend = computed<LegendEntry[]>(() =>
  props.segments.map((segment) => toEntry(segment.label, segment.count, segment.color, segment))
)

const totalEntry = computed<LegendEntry | undefined>(() =>
  props.total === undefined
    ? undefined
    : toEntry(props.total.label, totalCount.value, 'default', props.total)
)

const ariaLabel = computed<string>(() =>
  totalCount.value === 0
    ? _t('No services')
    : barSegments.value
        .map((segment) => _t('%{count} %{label}', { count: segment.count, label: segment.label }))
        .join(', ')
)
</script>

<template>
  <div class="cmk-state-count-bar" :class="`cmk-state-count-bar--size-${size}`">
    <div v-if="slots.heading || totalEntry" class="cmk-state-count-bar__header">
      <slot name="heading" />
      <component
        :is="totalEntry.href === undefined ? 'span' : 'a'"
        v-if="totalEntry"
        class="cmk-state-count-bar__total-entry"
        :href="totalEntry.href"
        :target="totalEntry.target"
      >
        {{ totalEntry.label }}: {{ totalEntry.count }}
      </component>
    </div>
    <div class="cmk-state-count-bar__bar" role="img" :aria-label="ariaLabel">
      <template v-if="totalCount > 0">
        <div
          v-for="(segment, index) in barSegments"
          :key="index"
          class="cmk-state-count-bar__segment"
          :class="`cmk-state-count-bar__segment--${segment.color}`"
          :style="{ flexGrow: segment.count }"
        />
      </template>
      <div
        v-else
        class="cmk-state-count-bar__segment cmk-state-count-bar__segment--empty"
        :style="{ flexGrow: 1 }"
      />
    </div>
    <ul class="cmk-state-count-bar__legend">
      <li v-for="(entry, index) in legend" :key="index" class="cmk-state-count-bar__legend-item">
        <component
          :is="entry.href === undefined ? 'span' : 'a'"
          class="cmk-state-count-bar__legend-entry"
          :href="entry.href"
          :target="entry.target"
        >
          <CmkColorSwatch :color="`var(--state-count-bar-${entry.color})`" />
          {{ entry.label }}: {{ entry.count }}
        </component>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cmk-state-count-bar {
  --state-count-bar-success: var(--color-corporate-green-80);
  --state-count-bar-warning: var(--color-yellow-60);
  --state-count-bar-danger: var(--color-dark-red-60);
  --state-count-bar-unknown: var(--color-orange-70);
  --state-count-bar-pending: var(--color-mist-grey-80);

  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.cmk-state-count-bar__header {
  display: flex;
  gap: var(--spacing);
  align-items: center;
  justify-content: space-between;
}

.cmk-state-count-bar__total-entry {
  margin-left: auto;
  color: var(--font-color);
  text-decoration: none;
  white-space: nowrap;
}

.cmk-state-count-bar__bar {
  display: flex;
  gap: var(--dimension-2);
  width: 100%;
  overflow: hidden;
  border-radius: var(--border-radius);
}

.cmk-state-count-bar--size-medium .cmk-state-count-bar__bar {
  height: var(--dimension-6);
}

.cmk-state-count-bar--size-small .cmk-state-count-bar__bar {
  height: var(--dimension-4);
}

.cmk-state-count-bar__segment {
  flex-basis: 0;
  height: 100%;
}

.cmk-state-count-bar__segment--success {
  background-color: var(--state-count-bar-success);
}

.cmk-state-count-bar__segment--warning {
  background-color: var(--state-count-bar-warning);
}

.cmk-state-count-bar__segment--danger {
  background-color: var(--state-count-bar-danger);
}

.cmk-state-count-bar__segment--unknown {
  background-color: var(--state-count-bar-unknown);
}

.cmk-state-count-bar__segment--pending {
  background-color: var(--state-count-bar-pending);
}

.cmk-state-count-bar__segment--default,
.cmk-state-count-bar__segment--empty {
  background-color: var(--state-count-bar-default);
}

.cmk-state-count-bar__legend {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3) calc(var(--spacing) + var(--dimension-4));
  padding: 0;
  margin: 0;
  list-style: none;
}

.cmk-state-count-bar__legend-entry {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-4);
  color: var(--font-color);
  text-decoration: none;
  white-space: nowrap;
}

a.cmk-state-count-bar__legend-entry:hover,
a.cmk-state-count-bar__total-entry:hover {
  text-decoration: underline;
}

body[data-theme='facelift'] .cmk-state-count-bar {
  --state-count-bar-default: var(--color-daylight-grey-50);
}

body[data-theme='modern-dark'] .cmk-state-count-bar {
  --state-count-bar-default: var(--color-midnight-grey-50);
}
</style>
