<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import StateTag, { type StateTone } from 'cmk-ui-library/components/StateTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, onMounted, ref, watch } from 'vue'

import KpiSparkLine from './KpiSparkLine.vue'
import type {
  CmkKpiStatCardProps,
  ComparisonBasis,
  KpiDelta,
  KpiStateSeverity,
  TimestampedSample
} from './types'

const props = withDefaults(defineProps<CmkKpiStatCardProps>(), {
  unit: undefined,
  series: () => [],
  delta: () => ({}),
  formatValue: (value: number) => value.toFixed(1),
  state: undefined,
  rangeLimits: undefined,
  range: undefined,
  href: undefined,
  sparkHeightMode: 'full'
})

const { _t } = usei18n()
const showDelta = computed(() => props.delta.show ?? true)
const comparisonBasis = computed(() => props.delta.comparisonBasis ?? 'average')

// Reuses the shared adaptive-unit formatter (the same one profiling's own
// formatDuration() wraps) rather than hand-rolling seconds -> "6h" maths.
const { formatter: durationFormatter } = userSpecificUnit(
  { notation: 'time', symbol: 's', precision: { type: 'auto', digits: 0 } },
  'celsius'
)

const BASIS_LABEL: Record<ComparisonBasis, () => TranslatedString> = {
  average: () => _t('avg.'),
  last: () => _t('prev. sample'),
  minimum: () => _t('min.'),
  maximum: () => _t('max.'),
  median: () => _t('median')
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? (sorted[mid - 1]! + sorted[mid]!) / 2 : sorted[mid]!
}

function computeBasisValue(basis: ComparisonBasis, values: number[]): number {
  switch (basis) {
    case 'average':
      return values.reduce((sum, value) => sum + value, 0) / values.length
    case 'last':
      return values[values.length - 1]!
    case 'minimum':
      return Math.min(...values)
    case 'maximum':
      return Math.max(...values)
    case 'median':
      return median(values)
  }
}

// The basis excludes the current sample itself - it is a comparison, not a
// self-inclusive average. Hidden below two real samples: one alone has
// nothing to compare against, and a zero basis has no meaningful ratio.
// Superseded by `delta.override` when given - see the `delta` computed below.
const seriesDelta = computed<KpiDelta | undefined>(() => {
  if (!showDelta.value) {
    return undefined
  }
  const realSamples = props.series.filter(
    (sample): sample is TimestampedSample & { value: number } => sample.value !== null
  )
  if (realSamples.length < 2) {
    return undefined
  }
  const currentSample = realSamples[realSamples.length - 1]!
  const basisSamples = realSamples.slice(0, -1)
  const basisValue = computeBasisValue(
    comparisonBasis.value,
    basisSamples.map((sample) => sample.value)
  )
  if (basisValue === 0) {
    return undefined
  }
  const ratio = (currentSample.value - basisValue) / basisValue
  // "prev. sample" is a single adjacent point, not a range - a window duration
  // describes a span being averaged/scanned, which doesn't apply to it.
  const comparisonText =
    comparisonBasis.value === 'last'
      ? _t('vs. %{basisValue} %{basisLabel}', {
          basisValue: props.formatValue(basisValue),
          basisLabel: BASIS_LABEL[comparisonBasis.value]()
        })
      : _t('vs. %{basisValue} %{basisLabel} (%{window})', {
          basisValue: props.formatValue(basisValue),
          basisLabel: BASIS_LABEL[comparisonBasis.value](),
          window: durationFormatter.render(currentSample.timestamp - basisSamples[0]!.timestamp)
        })
  return {
    percent: `${Math.abs(ratio * 100).toFixed(1)}%`,
    up: ratio >= 0,
    comparisonText
  }
})

// A caller-supplied delta takes priority over series-derived one; fromCaller uses
// delta.override exclusively so a per-render undefined stays empty, not a wrong fallback.
const delta = computed<KpiDelta | undefined>(() => {
  if (!showDelta.value) {
    return undefined
  }
  const override = props.delta.override
  return props.delta.fromCaller ? override : (override ?? seriesDelta.value)
})

const STATE_TAG_TONE: Record<KpiStateSeverity, StateTone> = {
  ok: 'ok',
  warn: 'warning',
  crit: 'critical',
  unknown: 'unknown',
  pending: 'pending'
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

// No state to color when there's no data at all - card colorization doesn't apply.
const hasData = computed(() => props.value !== undefined)
const tintColor = computed(() =>
  hasData.value && props.state?.tintBackground ? stateColor.value : undefined
)

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
// value takes the card to itself. No data at all means no curve either.
const hasSparkLine = computed(() => hasData.value && props.series.length >= 2)

// KpiSparkLine reports the focused real sample here while scrubbing; a tile with no
// curve has nothing to scrub.
const sparkLine = ref<InstanceType<typeof KpiSparkLine> | null>(null)
const hoveredSample = ref<TimestampedSample | undefined>(undefined)
// Drives the card-wide crosshair line - kept separate from KpiSparkLine's own dot,
// which band mode confines below the value/date text.
const hoveredXPercent = ref<number | undefined>(undefined)

function onSparkLineFocus(
  sample: TimestampedSample | undefined,
  xPercent: number | undefined
): void {
  hoveredSample.value = sample
  hoveredXPercent.value = xPercent
}

// formatValue's output may embed its own unit (e.g. "414.49 Mbps"), so split it like
// the headline value/unit or a hovered sample's unit doubles up with the static one.
const hoveredFormatted = computed<{ value: string; unit: string | undefined } | undefined>(() => {
  const sample = hoveredSample.value
  if (!sample) {
    return undefined
  }
  const rendered = props.formatValue(sample.value!)
  const spaceIndex = rendered.indexOf(' ')
  return spaceIndex === -1
    ? { value: rendered, unit: undefined }
    : { value: rendered.slice(0, spaceIndex), unit: rendered.slice(spaceIndex + 1) }
})

const hoveredValueText = computed<string | undefined>(() => hoveredFormatted.value?.value)

const hoveredTimeLabel = computed<string | undefined>(() => {
  const sample = hoveredSample.value
  if (!sample) {
    return undefined
  }
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(sample.timestamp * 1000)
})

// Scrubbing spans the whole card, so the card (not KpiSparkLine's SVG) owns pointer
// capture; KpiSparkLine still does the coordinate math.
function onCardPointerMove(event: PointerEvent): void {
  sparkLine.value?.focusFromPointerX(event.clientX)
}

function onCardPointerLeave(): void {
  sparkLine.value?.clearWithDelay()
}

// Curve-less metrics center the value to fill the card. No-data is
// different - it would normally plot a curve, so it stays top-left.
const isValueOnly = computed(() => hasData.value && props.series.length < 2)

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
watch(() => [props.value, props.unit, delta.value, hoveredSample.value], measureScrim, {
  flush: 'post'
})
onMounted(measureScrim)
</script>

<template>
  <div
    ref="cardEl"
    class="db-cmk-kpi-stat-card"
    :class="{
      'db-cmk-kpi-stat-card--tinted': tintColor !== undefined,
      'db-cmk-kpi-stat-card--value-only': isValueOnly,
      'db-cmk-kpi-stat-card--band': hasSparkLine && sparkHeightMode === 'band'
    }"
    :style="{
      '--accent-color': color,
      '--tint-color': tintColor,
      '--scrim-right-edge': `${scrimRightEdge}px`,
      '--scrim-bottom-edge': `${scrimBottomEdge}px`
    }"
    :tabindex="hasSparkLine ? 0 : undefined"
    @pointermove="hasSparkLine ? onCardPointerMove($event) : undefined"
    @pointerleave="hasSparkLine ? onCardPointerLeave() : undefined"
  >
    <div ref="valueRowEl" class="db-cmk-kpi-stat-card__value-row">
      <component :is="href ? 'a' : 'span'" :href="href" class="db-cmk-kpi-stat-card__value-link">
        <span class="db-cmk-kpi-stat-card__value">
          {{ hoveredValueText ?? (hasData ? value : '—') }}
        </span>
        <span
          v-if="hoveredFormatted ? (hoveredFormatted.unit ?? unit) : unit"
          class="db-cmk-kpi-stat-card__unit"
        >
          {{ hoveredFormatted ? (hoveredFormatted.unit ?? unit) : unit }}
        </span>
      </component>
      <div
        v-if="hasData && (hoveredSample || isStale || delta !== undefined)"
        class="db-cmk-kpi-stat-card__info-slot"
      >
        <span v-if="hoveredSample" class="db-cmk-kpi-stat-card__hover-note">
          {{ hoveredTimeLabel }}
        </span>
        <span v-else-if="isStale" class="db-cmk-kpi-stat-card__stale-note">
          <CmkIcon name="clock" size="small" :colored="false" />
          {{ _t('No recent data — last sample %{time}', { time: lastSampleTimeLabel ?? '' }) }}
        </span>
        <span
          v-else-if="delta"
          class="db-cmk-kpi-stat-card__delta"
          :class="{ 'db-cmk-kpi-stat-card__delta--down': !delta.up }"
        >
          <svg class="db-cmk-kpi-stat-card__delta-arrow" viewBox="0 0 8 6" aria-hidden="true">
            <path d="m0 6 4-6 4 6z" fill="currentColor" />
          </svg>
          <span class="db-cmk-kpi-stat-card__delta-percent">{{ delta.percent }}</span>
          <span class="db-cmk-kpi-stat-card__delta-comparison">{{ delta.comparisonText }}</span>
        </span>
      </div>
    </div>

    <p v-if="!hasData" class="db-cmk-kpi-stat-card__no-data-note">
      {{ _t('No data in this timeframe.') }}
    </p>

    <div v-if="showScrim" class="db-cmk-kpi-stat-card__scrim" aria-hidden="true" />

    <!-- Spans the whole card, not just KpiSparkLine's own box: in band mode
         that box only covers the area below the value/date text, but the
         crosshair itself should still reach the widget's actual top and bottom. -->
    <div
      v-if="hoveredXPercent !== undefined"
      class="db-cmk-kpi-stat-card__crosshair-line"
      :style="{ left: `${hoveredXPercent}%` }"
      aria-hidden="true"
    />

    <StateTag
      v-if="hasData && state && stateLabel"
      class="db-cmk-kpi-stat-card__state"
      :label="stateLabel"
      :tone="STATE_TAG_TONE[state.severity]"
      kind="service"
      :stale="isStale"
    />

    <div v-if="hasSparkLine" class="db-cmk-kpi-stat-card__spark-line">
      <KpiSparkLine
        ref="sparkLine"
        :series="series"
        :color="color"
        :fade-to-floor="tintColor !== undefined"
        :range="range"
        @focus="onSparkLineFocus"
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

/* Crosshair only where scrubbing does something - a tile without a curve (no
   [tabindex]) keeps the default cursor. */
.db-cmk-kpi-stat-card[tabindex] {
  cursor: crosshair;
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
  flex-direction: column;
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

/* Neutral: the delta makes no judgment about direction, only reports it, so it
   reads in the same dimmed color as the stale note it swaps places with. */
.db-cmk-kpi-stat-card__delta {
  display: inline-flex;
  flex-shrink: 0;
  gap: clamp(2px, 1cqw, 5px);
  align-items: center;
  min-width: 0;
  overflow: hidden;
  font-size: clamp(9px, 14cqh, 16px);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.db-cmk-kpi-stat-card__delta-percent {
  flex-shrink: 0;
  font-weight: var(--font-weight-bold);
}

/* The comparison text ("vs. 47.1% avg. (6h)") is the part most likely to be
   clipped in a narrow card - the percent and direction matter more. */
.db-cmk-kpi-stat-card__delta-comparison {
  overflow: hidden;
  text-overflow: ellipsis;
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

.db-cmk-kpi-stat-card__hover-note {
  overflow: hidden;
  font-size: clamp(9px, 14cqh, 16px);
  font-weight: var(--font-weight-bold);
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
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

.db-cmk-kpi-stat-card__no-data-note {
  margin: 0;

  /* Left-aligned under the value, not centered - this isn't a value-only card. */
  padding: 0 calc(var(--spacing) * 2);
  font-size: clamp(10px, 14cqh, 16px);
  color: var(--font-color-dimmed);
}

/* Same top-right corner in every variant, so a dashboard grid can be scanned by corner alone.
   Positioned against the card, so it must be a child of the card, not of the value row.
   Sizing is StateTag's own (the Views 3.0 state label): fixed, not scaled with card height
   like the old CmkBadge - StateTag exposes no scaling hook, so this is deliberate. */
.db-cmk-kpi-stat-card__state {
  position: absolute;
  top: var(--spacing);
  right: var(--spacing);
  z-index: 3;
  max-width: 40%;
}

/* Grey and dashed, not accent-colored: this marks a scrub position, not data -
   the curve and its own dot already carry the data color. Matches the
   graphing initiative's own crosshair exactly (setLineDash([3, 3]) at
   lineWidth 1) - a plain `dotted` border renders much tighter, browser-default
   spacing, so the dash/gap is drawn via a repeating gradient instead. */
.db-cmk-kpi-stat-card__crosshair-line {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 2;
  width: 1px;
  background-image: repeating-linear-gradient(
    to bottom,
    var(--font-color-dimmed) 0,
    var(--font-color-dimmed) 3px,
    transparent 3px,
    transparent 6px
  );
  pointer-events: none;
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
