<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge, { type Colors as CmkBadgeColor } from 'cmk-ui-library/components/CmkBadge.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, onMounted, ref, watch } from 'vue'

import KpiSparkLine from './KpiSparkLine.vue'
import type {
  CmkKpiStatCardProps,
  DeltaSemantics,
  KpiStateSeverity,
  TimestampedSample
} from './types'

const props = withDefaults(defineProps<CmkKpiStatCardProps>(), {
  unit: undefined,
  series: () => [],
  deltaRatio: undefined,
  deltaSemantics: 'neutral',
  state: undefined,
  rangeLimits: undefined,
  range: undefined,
  href: undefined,
  sparkHeightMode: 'full'
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

const lastRealSample = computed<TimestampedSample | undefined>(() =>
  [...props.series].reverse().find((d) => d.value !== null)
)

// A trailing null run means nothing has arrived since - stale. A null run
// bounded by real samples on both sides is just a gap, not stale.
const isStale = computed(
  () => lastRealSample.value !== undefined && props.series[props.series.length - 1]?.value === null
)

const lastSampleTimeLabel = computed<string | undefined>(() => {
  const sample = lastRealSample.value
  if (!sample) {
    return undefined
  }
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(
    sample.timestamp * 1000
  )
})

// A single point draws no line, so anything under two is "no plot" and the
// value takes the card to itself.
const hasSparkLine = computed(() => props.series.length >= 2)

// Band mode never overlaps the value row, so only full mode needs a scrim.
const showScrim = computed(() => hasSparkLine.value && props.sparkHeightMode === 'full')

const cardEl = ref<HTMLElement | null>(null)
const valueRowEl = ref<HTMLElement | null>(null)
// The value row's live edges - the scrim must stay within the text's own band, not the whole card.
const scrimRightEdge = ref(0)
const scrimBottomEdge = ref(0)

function measureScrim(): void {
  const card = cardEl.value
  const row = valueRowEl.value
  if (!card || !row) {
    return
  }
  const cardRect = card.getBoundingClientRect()
  const rowRect = row.getBoundingClientRect()
  scrimRightEdge.value = rowRect.right - cardRect.left
  scrimBottomEdge.value = rowRect.bottom - cardRect.top
}

const { observe } = useResizeObserver(measureScrim)
observe(valueRowEl)
watch(() => [props.value, props.unit, props.deltaRatio], measureScrim, { flush: 'post' })
onMounted(measureScrim)
</script>

<template>
  <div
    ref="cardEl"
    class="db-cmk-kpi-stat-card"
    :class="{
      'db-cmk-kpi-stat-card--tinted': tintColor !== undefined,
      'db-cmk-kpi-stat-card--value-only': !hasSparkLine,
      'db-cmk-kpi-stat-card--band': hasSparkLine && sparkHeightMode === 'band'
    }"
    :style="{
      '--accent-color': color,
      '--tint-color': tintColor,
      '--scrim-right-edge': `${scrimRightEdge}px`,
      '--scrim-bottom-edge': `${scrimBottomEdge}px`
    }"
  >
    <div ref="valueRowEl" class="db-cmk-kpi-stat-card__value-row">
      <component :is="href ? 'a' : 'span'" :href="href" class="db-cmk-kpi-stat-card__value-link">
        <span class="db-cmk-kpi-stat-card__value">{{ value }}</span>
        <span v-if="unit" class="db-cmk-kpi-stat-card__unit">{{ unit }}</span>
      </component>
      <div v-if="isStale || deltaRatio !== undefined" class="db-cmk-kpi-stat-card__info-slot">
        <span v-if="isStale" class="db-cmk-kpi-stat-card__stale-note">
          <CmkIcon name="clock" size="small" :colored="false" />
          {{ _t('No recent data — last sample %{time}', { time: lastSampleTimeLabel ?? '' }) }}
        </span>
        <span
          v-else-if="deltaRatio !== undefined"
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
    </div>

    <div v-if="showScrim" class="db-cmk-kpi-stat-card__scrim" aria-hidden="true" />

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

  /* The card's own background, shared with the full-height scrim below so the two can't drift apart. */
  --card-effective-bg: var(--db-content-bg-color);
}

.db-cmk-kpi-stat-card--tinted {
  /* Opaque (mixed against the real backdrop, not transparent), so the scrim can reuse it to block the curve. */
  --card-effective-bg: color-mix(in srgb, var(--tint-color) 12%, var(--db-content-bg-color));

  background-color: var(--card-effective-bg);
}

/* Full-bleed by default; band mode overrides this below. */
.db-cmk-kpi-stat-card__spark-line {
  position: absolute;
  inset: 0;
}

/* Band mode: a column layout instead of full mode's absolute overlap. */
.db-cmk-kpi-stat-card--band {
  display: flex;
  flex-direction: column;
}

.db-cmk-kpi-stat-card--band .db-cmk-kpi-stat-card__spark-line {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  inset: auto;
}

.db-cmk-kpi-stat-card__value-row {
  position: relative;
  z-index: 2;

  /* Stacked, not inline: the stale note can run long, so it gets its own row. */
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: clamp(2px, 1cqh, 6px);
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

  /* Neutral: the accent/data color belongs to the curve, not the number. */
  color: var(--font-color);
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

/* Delta and stale note share this slot; reserving height keeps the card from jumping when they swap. */
.db-cmk-kpi-stat-card__info-slot {
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  min-height: clamp(16px, 20cqh, 28px);
}

.db-cmk-kpi-stat-card__stale-note {
  display: inline-flex;
  gap: clamp(2px, 1cqw, 5px);
  align-items: center;
  min-width: 0;
  overflow: hidden;
  font-size: clamp(9px, 14cqh, 16px);
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* CmkBadge is sized for counts, so it pads to a bubble around a short label
   like "OK". Widen it to read as the state name it is.
   Same top-right corner in every variant, so a dashboard grid can be scanned by corner alone.
   Positioned against the card, so it must be a child of the card, not of the value row. */
.db-cmk-kpi-stat-card__state {
  position: absolute;
  top: var(--spacing);
  right: var(--spacing);
  z-index: 3;
  max-width: 40%;
  height: auto;
  padding: clamp(2px, 3cqh, 7px) clamp(8px, 3cqw, 18px);
  margin: 0;
  font-size: clamp(11px, 18cqh, 24px);
  font-weight: var(--font-weight-bold);
  line-height: 1.4;
}

/* Fades out in both directions past the text, so a curve peak near it isn't sliced off flat. */
.db-cmk-kpi-stat-card__scrim {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: calc(var(--scrim-bottom-edge) + clamp(8px, 6cqh, 32px));
  z-index: 1;
  background: linear-gradient(
    to right,
    var(--card-effective-bg) 0,
    var(--card-effective-bg) var(--scrim-right-edge),
    transparent calc(var(--scrim-right-edge) + clamp(8px, 6cqw, 32px))
  );
  mask-image: linear-gradient(
    to bottom,
    black 0,
    black var(--scrim-bottom-edge),
    transparent calc(var(--scrim-bottom-edge) + clamp(8px, 6cqh, 32px))
  );
  pointer-events: none;
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
