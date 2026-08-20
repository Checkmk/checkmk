<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge, { type Colors as CmkBadgeColor } from 'cmk-ui-library/components/CmkBadge.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import KpiSparkLine from './KpiSparkLine.vue'
import type { CmkKpiStatCardProps, DeltaSemantics, KpiStateSeverity } from './types'

const props = withDefaults(defineProps<CmkKpiStatCardProps>(), {
  unit: undefined,
  series: () => [],
  deltaRatio: undefined,
  deltaSemantics: 'neutral',
  state: undefined,
  rangeLimits: undefined,
  range: undefined,
  href: undefined
})

const isUp = computed(() => (props.deltaRatio ?? 0) >= 0)
const deltaPercent = computed(() => `${Math.abs((props.deltaRatio ?? 0) * 100).toFixed(1)}%`)

const DELTA_NEUTRAL = 'var(--color-mid-grey-50)'
const DELTA_IMPROVED = 'var(--color-corporate-green-50)'
const DELTA_WORSENED = 'var(--color-light-red-50)'

// Neutral metrics make no judgment about direction; for good/bad metrics the
// direction is judged against what an increase means (up on an "up is bad"
// metric renders red).
function resolveDeltaColor(semantics: DeltaSemantics, up: boolean): string {
  switch (semantics) {
    case 'neutral':
      return DELTA_NEUTRAL
    case 'good':
      return up ? DELTA_IMPROVED : DELTA_WORSENED
    case 'bad':
      return up ? DELTA_WORSENED : DELTA_IMPROVED
  }
}

const deltaColor = computed(() => resolveDeltaColor(props.deltaSemantics, isUp.value))

const { _t } = usei18n()

// Checkmk's monitoring state colors, UNKNOWN among them -- orange, rather than
// the grey a generic "default" would give it.
const STATE_BADGE_COLOR: Record<KpiStateSeverity, CmkBadgeColor> = {
  ok: 'success',
  warn: 'warning',
  crit: 'danger',
  unknown: 'unknown',
  pending: 'default'
}

// The raw color behind the badge, for the card's optional tint.
const STATE_CSS_COLOR: Record<KpiStateSeverity, string> = {
  ok: 'var(--success)',
  warn: 'var(--color-warning)',
  crit: 'var(--color-danger)',
  unknown: 'var(--color-unknown)',
  pending: 'var(--color-midnight-grey-50)'
}

const stateLabel = computed<TranslatedString | undefined>(() => {
  switch (props.state?.severity) {
    case 'ok':
      return _t('OK')
    case 'warn':
      return _t('WARN')
    case 'crit':
      return _t('CRIT')
    case 'unknown':
      return _t('UNKN')
    case 'pending':
      return _t('PEND')
    default:
      return undefined
  }
})

const stateColor = computed(() => (props.state ? STATE_CSS_COLOR[props.state.severity] : undefined))

const tintColor = computed(() => (props.state?.tintBackground ? stateColor.value : undefined))

// A single point draws no line, so anything under two is "no plot" and the
// value takes the card to itself.
const hasSparkLine = computed(() => props.series.length >= 2)
</script>

<template>
  <div
    class="db-cmk-kpi-stat-card"
    :class="{
      'db-cmk-kpi-stat-card--tinted': tintColor !== undefined,
      'db-cmk-kpi-stat-card--value-only': !hasSparkLine
    }"
    :style="{ '--accent-color': color, '--tint-color': tintColor }"
  >
    <div class="db-cmk-kpi-stat-card__value-row">
      <component :is="href ? 'a' : 'span'" :href="href" class="db-cmk-kpi-stat-card__value-link">
        <span class="db-cmk-kpi-stat-card__value">{{ value }}</span>
        <span v-if="unit" class="db-cmk-kpi-stat-card__unit">{{ unit }}</span>
      </component>
      <span
        v-if="deltaRatio !== undefined"
        class="db-cmk-kpi-stat-card__pill db-cmk-kpi-stat-card__delta"
        :class="{ 'db-cmk-kpi-stat-card__delta--down': !isUp }"
        :style="{ '--pill-color': deltaColor }"
      >
        <svg class="db-cmk-kpi-stat-card__delta-arrow" viewBox="0 0 8 6" aria-hidden="true">
          <path d="m0 6 4-6 4 6z" fill="currentColor" />
        </svg>
        {{ deltaPercent }}
      </span>
    </div>

    <CmkBadge
      v-if="state && stateLabel"
      class="db-cmk-kpi-stat-card__state"
      :color="STATE_BADGE_COLOR[state.severity]"
      size="medium"
    >
      {{ stateLabel }}
    </CmkBadge>

    <div v-if="hasSparkLine" class="db-cmk-kpi-stat-card__spark-line">
      <KpiSparkLine
        :series="series"
        :color="color"
        :fade-to-floor="tintColor !== undefined"
        :range="range"
      />
      <template v-if="rangeLimits">
        <span class="db-cmk-kpi-stat-card__range db-cmk-kpi-stat-card__range--maximum">
          {{ rangeLimits.maximum }}
        </span>
        <span class="db-cmk-kpi-stat-card__range db-cmk-kpi-stat-card__range--minimum">
          {{ rangeLimits.minimum }}
        </span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.db-cmk-kpi-stat-card {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;

  /* Size containment lets the content scale to the widget via container query
     units (cqh/cqw) instead of overflowing and triggering scrollbars. */
  container-type: size;
}

.db-cmk-kpi-stat-card--tinted {
  /* Kept faint: the spark line's own gradient sits on top of it, and a heavier
     wash turns the two colors muddy. */
  background-color: color-mix(in srgb, var(--tint-color) 12%, transparent);
}

.db-cmk-kpi-stat-card__value-row {
  position: relative;
  z-index: 1;
  display: flex;
  gap: clamp(4px, 1.5cqw, 10px);
  align-items: baseline;
  min-width: 0;

  /* The card itself is full-bleed, so that a tinted background and the spark
     line reach the edges of whatever box it was given; the inset lives here. */
  padding: calc(var(--spacing) * 2);
}

.db-cmk-kpi-stat-card__value-link {
  display: inline-flex;
  flex-shrink: 0;
  gap: clamp(4px, 1.5cqw, 10px);
  align-items: baseline;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.db-cmk-kpi-stat-card__value {
  font-size: clamp(18px, min(40cqh, 16cqw), 52px);
  font-weight: var(--font-weight-bold);
  line-height: 1;
  color: var(--accent-color);
}

.db-cmk-kpi-stat-card__unit {
  font-size: clamp(10px, 16cqh, 22px);
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
}

/* With no plot to leave room for, the value has the whole card: centered, and
   scaled to the height it actually got rather than to the 45% a plot would have
   left it. */
.db-cmk-kpi-stat-card--value-only {
  display: flex;
  gap: clamp(4px, 1.5cqw, 10px);
  align-items: center;
  justify-content: center;
}

.db-cmk-kpi-stat-card--value-only .db-cmk-kpi-stat-card__value-row {
  justify-content: center;
}

.db-cmk-kpi-stat-card--value-only .db-cmk-kpi-stat-card__value {
  /* Bounded by width as well as height: the row also carries the unit and the
     state badge, and an over-wide value would be clipped rather than shrunk. */
  font-size: clamp(18px, min(46cqh, 18cqw), 96px);
}

.db-cmk-kpi-stat-card--value-only .db-cmk-kpi-stat-card__unit {
  font-size: clamp(10px, min(18cqh, 7cqw), 38px);
}

/* Delta and state read as siblings: same shape, same weight, tinted in whatever
   each one is saying. */
.db-cmk-kpi-stat-card__pill {
  display: inline-flex;
  gap: clamp(2px, 1cqw, 5px);
  align-items: center;
  align-self: center;
  min-width: 0;
  padding: clamp(1px, 2cqh, 4px) clamp(4px, 1.5cqw, 10px);
  overflow: hidden;
  font-size: clamp(9px, 14cqh, 16px);
  font-weight: var(--font-weight-bold);
  line-height: 1.4;
  color: var(--pill-color);
  text-overflow: ellipsis;
  white-space: nowrap;
  background-color: color-mix(in srgb, var(--pill-color) 15%, transparent);
  border-radius: 99999px;
}

.db-cmk-kpi-stat-card__delta {
  flex-shrink: 0;
}

.db-cmk-kpi-stat-card__delta-arrow {
  flex-shrink: 0;
  width: clamp(6px, 1cqw, 9px);
  height: clamp(5px, 0.8cqw, 7px);
}

.db-cmk-kpi-stat-card__delta--down .db-cmk-kpi-stat-card__delta-arrow {
  transform: rotate(180deg);
}

/* CmkBadge is sized for counts, so it pads to a bubble around a short label
   like "OK". Widen it to read as the state name it is.
   Beside the value by default, which is where a card with no plot has room for
   it -- there the value is centered and would collide with a centered badge. */
.db-cmk-kpi-stat-card__state {
  flex-shrink: 0;
  align-self: center;
  height: auto;
  padding: clamp(2px, 3cqh, 7px) clamp(8px, 3cqw, 18px);
  margin: 0;
  font-size: clamp(11px, 18cqh, 24px);
  font-weight: var(--font-weight-bold);
  line-height: 1.4;
}

/* With a plot underneath, it floats over the middle of the card instead: it
   qualifies the whole widget rather than the number. Positioned against the
   card, so it must be a child of the card and not of the value row. */
.db-cmk-kpi-stat-card:not(.db-cmk-kpi-stat-card--value-only) .db-cmk-kpi-stat-card__state {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 2;
  max-width: 90%;
  transform: translate(-50%, -50%);
}

.db-cmk-kpi-stat-card__spark-line {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 55%;
}

/* Labels for the ends of the plotted range, so they sit against the plot rather
   than the card. Right-aligned, away from where the spark line starts. */
.db-cmk-kpi-stat-card__range {
  position: absolute;
  right: calc(var(--spacing) * 2);
  font-size: clamp(8px, 9cqh, 11px);
  line-height: 1;
  color: var(--font-color-dimmed);
  pointer-events: none;
  opacity: 0.8;
}

.db-cmk-kpi-stat-card__range--maximum {
  top: var(--spacing);
}

.db-cmk-kpi-stat-card__range--minimum {
  bottom: var(--spacing);
}
</style>
