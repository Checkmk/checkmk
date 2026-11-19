<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, watch } from 'vue'

import { useSharedResizeObserver } from '../../composables/useSharedResizeObserver'
import MetricAttributeGroups from '../MetricAttributeGroups.vue'
import type { HorizontalLine, Metric, ShadedRegion } from '../TimeSeriesGraph'
import { type MetricAttribute, attributesOf } from '../metricAttributes'
import { orderMetricsTopToBottom } from '../metricOrder'
import GraphLegendEyeButton from './GraphLegendEyeButton.vue'
import { withNameToggled } from './legendUtils'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    metrics: Metric[]
    horizontalLines?: HorizontalLine[]
    shadedRegions?: ShadedRegion[]
    hiddenMetricNames?: string[]
    hiddenLineNames?: string[]
    clickableMetricNames?: string[]
  }>(),
  {
    horizontalLines: () => [],
    shadedRegions: () => [],
    hiddenMetricNames: () => [],
    hiddenLineNames: () => [],
    clickableMetricNames: () => []
  }
)

const emit = defineEmits<{
  'update:hiddenMetricNames': [value: string[]]
  'update:hiddenLineNames': [value: string[]]
  hoverMetrics: [names: string[]]
  metricClick: [metricName: string]
}>()

const DISTINCTIVE_TAIL_CHARS = 5
const MIN_VISIBLE_HEAD_CHARS = 12
const ESTIMATED_CHAR_WIDTH_EM = 0.45

const EYE_BUTTON_WIDTH_PX = 20
const ITEM_GAP_PX = 2
const SWATCH_WIDTH_PX = 4
const SERIES_GAP_PX = 5
const ITEM_CHROME_WIDTH_PX = EYE_BUTTON_WIDTH_PX + ITEM_GAP_PX + SWATCH_WIDTH_PX + SERIES_GAP_PX

function splitForMiddleTruncation(title: string): { nameHead: string; nameTail: string } {
  if (title.length <= DISTINCTIVE_TAIL_CHARS * 2) {
    return { nameHead: title, nameTail: '' }
  }
  return {
    nameHead: title.slice(0, -DISTINCTIVE_TAIL_CHARS),
    nameTail: title.slice(-DISTINCTIVE_TAIL_CHARS)
  }
}

function itemMinWidth(nameHead: string, nameTail: string): string {
  const alwaysVisibleChars = Math.min(MIN_VISIBLE_HEAD_CHARS, nameHead.length) + nameTail.length
  return `calc(${ITEM_CHROME_WIDTH_PX}px + ${alwaysVisibleChars * ESTIMATED_CHAR_WIDTH_EM}em)`
}

interface CompactLegendItem {
  key: string
  title: string
  nameHead: string
  nameTail: string
  minWidth: string
  color: string
  hidden: boolean
  metricName: string | null
  clickable: boolean
  /** Empty for threshold lines and for RRD metrics. */
  attributes: MetricAttribute[]
  toggle: () => void
}

function withTruncationLayout(
  item: Omit<CompactLegendItem, 'nameHead' | 'nameTail' | 'minWidth'>
): CompactLegendItem {
  const { nameHead, nameTail } = splitForMiddleTruncation(item.title)
  return { ...item, nameHead, nameTail, minWidth: itemMinWidth(nameHead, nameTail) }
}

const items = computed((): CompactLegendItem[] => [
  ...orderMetricsTopToBottom(props.metrics).map((metric) =>
    withTruncationLayout({
      key: `metric:${metric.metadata.name}`,
      title: metric.metadata.title,
      color: metric.metadata.color,
      hidden: props.hiddenMetricNames.includes(metric.metadata.name),
      metricName: metric.metadata.name,
      clickable: props.clickableMetricNames.includes(metric.metadata.name),
      attributes: attributesOf(metric),
      toggle: () =>
        emit(
          'update:hiddenMetricNames',
          withNameToggled(props.hiddenMetricNames, metric.metadata.name)
        )
    })
  ),
  ...props.horizontalLines.map((line) =>
    withTruncationLayout({
      key: `line:${line.name}`,
      title: line.title,
      color: line.color,
      hidden: props.hiddenLineNames.includes(line.name),
      metricName: null,
      clickable: false,
      attributes: [],
      toggle: () =>
        emit('update:hiddenLineNames', withNameToggled(props.hiddenLineNames, line.name))
    })
  ),
  ...props.shadedRegions.map((region) =>
    withTruncationLayout({
      key: `region:${region.name}`,
      title: region.title,
      color: region.color,
      hidden: false,
      metricName: null,
      clickable: false,
      attributes: [],
      toggle: () => {}
    })
  )
])

const itemsRow = ref<HTMLElement | null>(null)
const canScrollBack = ref(false)
const canScrollForward = ref(false)
const overflowing = computed(() => canScrollBack.value || canScrollForward.value)

function updateScrollState(): void {
  const row = itemsRow.value
  if (row === null) {
    return
  }
  canScrollBack.value = row.scrollLeft > 0
  // Fractional layouts can stop the scroll a sub-pixel short of scrollWidth -> -1 as tolerance
  canScrollForward.value = row.scrollLeft + row.clientWidth < row.scrollWidth - 1
}

useSharedResizeObserver(itemsRow, updateScrollState)
watch(items, () => void nextTick(updateScrollState))

const SCROLL_STEP_SHARE = 0.8
const scrollBackLabel = _t('Scroll legend back')
const scrollForwardLabel = _t('Scroll legend forward')

function scrollByStep(direction: -1 | 1): void {
  itemsRow.value?.scrollBy({
    left: direction * itemsRow.value.clientWidth * SCROLL_STEP_SHARE,
    behavior: 'smooth'
  })
}

const openAttributesKey = ref<string | null>(null)

function setAttributesOpen(key: string, open: boolean): void {
  openAttributesKey.value = open ? key : null
}

function onItemEnter(item: CompactLegendItem): void {
  if (item.metricName !== null) {
    emit('hoverMetrics', [item.metricName])
  }
}

function onItemLeave(item: CompactLegendItem): void {
  if (item.metricName !== null) {
    emit('hoverMetrics', [])
  }
}

function onNameClick(item: CompactLegendItem): void {
  if (item.metricName !== null) {
    emit('metricClick', item.metricName)
  }
}
</script>

<template>
  <CmkTooltipProvider :delay-duration="300">
    <div class="graphing-graph-legend-compact">
      <CmkButton
        v-if="overflowing"
        variant="secondary"
        size="iconOnly"
        class="graphing-graph-legend-compact__scroll-step graphing-graph-legend-compact__scroll-step--back"
        :disabled="!canScrollBack"
        :title="scrollBackLabel"
        :aria-label="scrollBackLabel"
        @click="scrollByStep(-1)"
      >
        <ArrowDown class="graphing-graph-legend-compact__scroll-caret" aria-hidden="true" />
      </CmkButton>
      <div
        ref="itemsRow"
        class="graphing-graph-legend-compact__items"
        role="group"
        :aria-label="_t('Graph metrics')"
        @scroll.passive="updateScrollState"
      >
        <div
          v-for="item in items"
          :key="item.key"
          class="graphing-graph-legend-compact__item"
          :class="{ 'graphing-graph-legend-compact__item--hidden': item.hidden }"
          :style="{ minWidth: item.minWidth }"
          @mouseenter="onItemEnter(item)"
          @mouseleave="onItemLeave(item)"
        >
          <GraphLegendEyeButton
            :hidden="item.hidden"
            :aria-label="item.title"
            @toggle="item.toggle()"
          />
          <!-- A chip row has no room to expand inline; portalled so its scroll cannot clip it. -->
          <CmkTooltip
            :open="openAttributesKey === item.key"
            @update:open="setAttributesOpen(item.key, $event)"
          >
            <CmkTooltipTrigger as-child>
              <!-- Focusable only when there is something to reveal, so no dead tab stop. -->
              <span
                class="graphing-graph-legend-compact__series"
                :class="{
                  'graphing-graph-legend-compact__series--has-attributes':
                    item.attributes.length > 0
                }"
                :title="item.title"
                :tabindex="item.attributes.length > 0 ? 0 : undefined"
              >
                <span
                  class="graphing-graph-legend-compact__swatch"
                  :style="{ background: item.color }"
                />
                <component
                  :is="item.clickable ? 'button' : 'span'"
                  class="graphing-graph-legend-compact__name"
                  :class="{ 'graphing-graph-legend-compact__name--clickable': item.clickable }"
                  :type="item.clickable ? 'button' : undefined"
                  :aria-label="
                    item.clickable
                      ? _t('Show details for %{metric}', { metric: item.title })
                      : undefined
                  "
                  @click="item.clickable && onNameClick(item)"
                >
                  <span class="graphing-graph-legend-compact__name-head">{{ item.nameHead }}</span
                  ><span class="graphing-graph-legend-compact__name-tail">{{ item.nameTail }}</span>
                </component>
              </span>
            </CmkTooltipTrigger>
            <CmkTooltipContent
              v-if="item.attributes.length > 0"
              variant="content"
              :title="untranslated(item.title)"
              use-portal
            >
              <MetricAttributeGroups
                class="graphing-graph-legend-compact__attributes"
                :attributes="item.attributes"
              />
            </CmkTooltipContent>
          </CmkTooltip>
        </div>
      </div>
      <CmkButton
        v-if="overflowing"
        variant="secondary"
        size="iconOnly"
        class="graphing-graph-legend-compact__scroll-step graphing-graph-legend-compact__scroll-step--forward"
        :disabled="!canScrollForward"
        :title="scrollForwardLabel"
        :aria-label="scrollForwardLabel"
        @click="scrollByStep(1)"
      >
        <ArrowDown class="graphing-graph-legend-compact__scroll-caret" aria-hidden="true" />
      </CmkButton>
    </div>
  </CmkTooltipProvider>
</template>

<style scoped lang="scss">
/* Styled like the graph's time axis band. */
.graphing-graph-legend-compact {
  display: flex;
  align-items: center;
  font-size: var(--font-size-normal);
  color: var(--font-color);
  background-color: var(--ux-theme-5);

  /* Nested to outrank CmkButton's equally specific scoped variant styles. */
  .graphing-graph-legend-compact__scroll-step {
    flex: 0 0 auto;
    position: relative;
    height: 100%;
    max-width: var(--dimension-7);
    background-color: var(--ux-theme-5);
    border-color: transparent;

    &:hover:enabled {
      background-color: var(--ux-theme-5);
      background-image: linear-gradient(var(--background-hover-wash), var(--background-hover-wash));
    }

    &:disabled {
      cursor: default;
      opacity: 0.35;
    }

    /* Fades out the legend content running up to the button, so none collides with it. */
    &::after {
      content: '';
      position: absolute;
      z-index: 1;
      top: 0;
      bottom: 0;
      width: var(--dimension-8);
      pointer-events: none;
    }
  }
}

.graphing-graph-legend-compact__items {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--spacing-half);
  overflow-x: auto;
  scrollbar-width: none;
}

.graphing-graph-legend-compact__scroll-caret {
  width: var(--dimension-4);
}

.graphing-graph-legend-compact__scroll-step--back {
  .graphing-graph-legend-compact__scroll-caret {
    transform: rotate(90deg);
  }

  &::after {
    left: calc(100% + var(--border-width-1));
    background: linear-gradient(to right, var(--ux-theme-5), transparent);
  }
}

.graphing-graph-legend-compact__scroll-step--forward {
  .graphing-graph-legend-compact__scroll-caret {
    transform: rotate(-90deg);
  }

  &::after {
    right: calc(100% + var(--border-width-1));
    background: linear-gradient(to left, var(--ux-theme-5), transparent);
  }
}

.graphing-graph-legend-compact__item {
  flex: 0 1 auto;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  border-radius: var(--border-radius);

  &:hover {
    background: rgb(0 0 0 / 4%);
  }

  &--hidden {
    opacity: 0.45;
  }

  > :deep(.graphing-graph-legend-eye-button) {
    flex: 0 0 auto;
  }
}

.graphing-graph-legend-compact__series {
  flex: 0 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-half);

  &--has-attributes {
    cursor: help;

    &:focus-visible {
      outline: revert;
    }
  }
}

.graphing-graph-legend-compact__swatch {
  flex: 0 0 auto;
  width: 4px;
  height: 16px;
  border-radius: var(--border-radius);
}

.graphing-graph-legend-compact__name {
  display: flex;
  min-width: 0;

  &--clickable {
    padding: 0;
    border: none;
    background: none;
    font: inherit;
    color: inherit;
    cursor: pointer;

    &:hover {
      color: var(--success);
    }

    &:focus-visible {
      outline: revert;
    }
  }
}

.graphing-graph-legend-compact__name-head {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre;
}

.graphing-graph-legend-compact__name-tail {
  flex: 0 0 auto;
  white-space: pre;
}

.graphing-graph-legend-compact__attributes {
  z-index: var(--z-index-tooltip-offset);
  max-width: 420px;
  max-height: 50vh;
  overflow-y: auto;
}
</style>
