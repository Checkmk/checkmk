<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, ref, watch } from 'vue'

import GadgetRenderer from '@/maps/map/components/GadgetRenderer.vue'
import { useMetricUnits } from '@/maps/map/composables/useMetricUnits'
import { usePerfometer } from '@/maps/map/composables/usePerfometer'
import type { DataElement, ObjectState, PresentationElement } from '@/maps/types/api'
import { stateColor } from '@/maps/utils/stateColors'

import { bindingLabel, isBoundElement, isMetriclessBinding } from '../binding'
import { resolveImageRef } from '../elements'

const { _t } = usei18n()

const props = defineProps<{
  element: PresentationElement
  state: ObjectState | undefined
  // The element's own connection or the map's, for the perfometer lookup.
  connectionId?: string | null
  // Demo data for an unbound data slot; never set in view mode.
  sampleState?: ObjectState | undefined
  editingText?: boolean
}>()

const emit = defineEmits<{ 'text-change': [string] }>()

const textRef = ref<HTMLElement | null>(null)

function resolve(color: string | null | undefined, fallbackVar: string): string {
  return color && color.length > 0 ? color : `var(${fallbackVar})`
}

const effectiveState = computed(() => props.state ?? props.sampleState)

// Group/BI bindings have no perf metrics, so a gauge or bar would permanently
// render "—" — they fall back to the state light.
const effectiveGadgetType = computed(() => {
  const el = props.element
  if (el.kind !== 'data') {
    return 'gauge'
  }
  return isMetriclessBinding(el) ? 'trafficlight' : (el.display.gadget_type ?? 'gauge')
})

// The perfometer fills the dial where the raw perf_data has no max, and
// supplies the CMK-formatted caption.
const gadgetBinding = {
  connectionId: () => props.connectionId,
  hostName: () => (props.element.kind === 'data' ? props.element.host_name : null),
  serviceDescription: () =>
    props.element.kind === 'data' ? props.element.service_description : null,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command,
  enabled: () =>
    props.element.kind === 'data' &&
    props.element.display.mode === 'gadget' &&
    ['gauge', 'bar'].includes(effectiveGadgetType.value)
}
const perfometer = usePerfometer(gadgetBinding)
// Registered display units, so the readout matches the Checkmk GUI.
const metricUnits = useMetricUnits({
  ...gadgetBinding,
  enabled: () =>
    props.element.kind === 'data' &&
    props.element.display.mode === 'gadget' &&
    effectiveGadgetType.value !== 'trafficlight'
})
// The sample perf_data carries exactly one metric; the gadget needs its name
// to render a value rather than an empty dial.
const sampleMetric = computed(() => {
  const pd = props.sampleState?.perf_data ?? ''
  return pd.split('=')[0] || null
})

// A bound shape colours its primary surface by the live state, overriding the
// manual colour.
const shapeStateColor = computed(() =>
  props.element.kind === 'shape' && (isBoundElement(props.element) || props.sampleState)
    ? stateColor(effectiveState.value?.state)
    : null
)

const fillColor = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') {
    return 'none'
  }
  if (el.shape === 'line' || el.shape === 'arrow') {
    return 'none'
  }
  if (shapeStateColor.value) {
    return shapeStateColor.value
  }
  return resolve(el.fill, '--pres-shape-fill')
})
const strokeColor = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') {
    return 'none'
  }
  if ((el.shape === 'line' || el.shape === 'arrow') && shapeStateColor.value) {
    return shapeStateColor.value
  }
  return resolve(el.stroke, '--pres-shape-stroke')
})

const shapeLabelShow = computed(
  () => props.element.kind === 'shape' && (props.element.label?.show ?? false)
)
const shapeLabelText = computed(() => {
  const el = props.element
  if (el.kind !== 'shape') {
    return ''
  }
  return el.label?.text || effectiveState.value?.state || bindingLabel(el) || ''
})
const shapeLabelStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'shape' || !el.label) {
    return {}
  }
  return {
    color: resolve(el.label.color, '--pres-fg'),
    background: el.label.background ?? 'transparent',
    fontSize: `${el.label.size}px`,
    fontWeight: el.label.weight ?? 'normal',
    textAlign: el.label.align ?? 'center'
  }
})
const strokeInset = computed(() =>
  props.element.kind === 'shape' ? props.element.stroke_width / 2 : 0
)
const dashArray = computed(() => {
  if (props.element.kind !== 'shape') {
    return undefined
  }
  const w = props.element.stroke_width
  if (props.element.dash === 'dashed') {
    return `${w * 3} ${w * 2}`
  }
  if (props.element.dash === 'dotted') {
    return `${w} ${w * 1.5}`
  }
  return undefined
})

const textStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'text') {
    return {}
  }
  return {
    color: resolve(el.color, '--pres-fg'),
    background: el.background ?? 'transparent',
    fontFamily: el.font_family ?? 'var(--pres-font)',
    fontSize: `${el.font_size}px`,
    fontWeight: el.font_weight,
    fontStyle: el.font_style,
    textAlign: el.text_align,
    lineHeight: String(el.line_height),
    letterSpacing: `${el.letter_spacing}px`
  }
})

const imageSrc = computed(() =>
  props.element.kind === 'image' ? resolveImageRef(props.element.src) : ''
)

const imageStyle = computed(() => ({
  objectFit:
    props.element.kind === 'image' ? (props.element.fit as 'cover' | 'contain' | 'fill') : 'contain'
}))

// What the card spends on something other than the gadget: the padding of
// ``__data`` on both sides, and — when a label shows — its line plus the flex
// gap above it. Leaving the gap out made the gadget exactly one gap too tall,
// so a traffic light came to rest on top of its own caption.
const DATA_PADDING = 24
const DATA_GAP = 6
const LABEL_HEIGHT = 30

function chromeHeight(el: DataElement): number {
  return el.label?.show ? DATA_PADDING + DATA_GAP + LABEL_HEIGHT : DATA_PADDING
}

// Each gadget renders a different height per unit size — the traffic light
// stacks three bulbs, the gauge is a half-disc, the bar a thin track — so the
// size is divided by that factor or a traffic light overflows its card.
const gadgetSize = computed(() => {
  const el = props.element
  if (el.kind !== 'data') {
    return 40
  }
  const availW = el.w - 28
  const availH = el.h - chromeHeight(el)
  const gt = effectiveGadgetType.value
  const hFactor = gt === 'trafficlight' ? 1.85 : gt === 'bar' ? 0.55 : gt === 'value' ? 0.4 : 0.7
  return Math.max(36, Math.min(availW, availH / hFactor))
})

const iconSize = computed(() => {
  const el = props.element
  if (el.kind !== 'data') {
    return 36
  }
  return Math.max(20, Math.min(96, Math.min(el.w - 28, el.h - chromeHeight(el)) * 0.55))
})

const stateClr = computed(() => stateColor(effectiveState.value?.state))
const stateText = computed(() => effectiveState.value?.state ?? _t('PENDING'))

const dataBoxStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'data') {
    return {}
  }
  return {
    background: el.fill ? el.fill : 'var(--pres-shape-fill)',
    border: `2px solid ${stateClr.value}`
  }
})

const showLabel = computed(
  () => props.element.kind === 'data' && (props.element.label?.show ?? false)
)
const labelText = computed(() => {
  const el = props.element
  if (el.kind !== 'data') {
    return ''
  }
  return (
    el.label?.text ||
    el.name ||
    bindingLabel(el) ||
    (props.sampleState ? _t('Sample') : _t('Unbound'))
  )
})
const labelStyle = computed(() => {
  const el = props.element
  if (el.kind !== 'data' || !el.label) {
    return {}
  }
  return {
    color: resolve(el.label.color, '--pres-fg'),
    background: el.label.background ?? 'transparent',
    fontSize: `${el.label.size}px`,
    fontWeight: el.label.weight ?? 'normal',
    textAlign: el.label.align ?? 'center'
  }
})

watch(
  () => props.editingText,
  async (on) => {
    if (!on) {
      return
    }
    await nextTick()
    const el = textRef.value
    if (!el) {
      return
    }
    el.focus()
    const range = document.createRange()
    range.selectNodeContents(el)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
  }
)

// Reported even when unchanged: the parent ends editing on this, and only
// commits on a real change. Otherwise an untouched text box stays in edit mode.
function onTextBlur(): void {
  if (props.element.kind !== 'text' || !textRef.value) {
    return
  }
  emit('text-change', textRef.value.innerText)
}
</script>

<template>
  <template v-if="element.kind === 'shape'">
    <svg
      class="maps-presentation-element-view__svg"
      :width="element.w"
      :height="element.h"
      :viewBox="`0 0 ${element.w} ${element.h}`"
      preserveAspectRatio="none"
    >
      <rect
        v-if="element.shape === 'rect'"
        :x="strokeInset"
        :y="strokeInset"
        :width="Math.max(0, element.w - element.stroke_width)"
        :height="Math.max(0, element.h - element.stroke_width)"
        :rx="element.corner_radius"
        :fill="fillColor"
        :stroke="strokeColor"
        :stroke-width="element.stroke_width"
        :stroke-dasharray="dashArray"
      />
      <ellipse
        v-else-if="element.shape === 'ellipse'"
        :cx="element.w / 2"
        :cy="element.h / 2"
        :rx="Math.max(0, element.w / 2 - element.stroke_width / 2)"
        :ry="Math.max(0, element.h / 2 - element.stroke_width / 2)"
        :fill="fillColor"
        :stroke="strokeColor"
        :stroke-width="element.stroke_width"
        :stroke-dasharray="dashArray"
      />
      <template v-else>
        <line
          :x1="0"
          :y1="element.h / 2"
          :x2="element.shape === 'arrow' ? element.w - 12 : element.w"
          :y2="element.h / 2"
          :stroke="strokeColor"
          :stroke-width="element.stroke_width"
          :stroke-dasharray="dashArray"
          stroke-linecap="round"
        />
        <polygon
          v-if="element.shape === 'arrow'"
          :points="`${element.w - 14},${element.h / 2 - 8} ${element.w},${element.h / 2} ${element.w - 14},${element.h / 2 + 8}`"
          :fill="strokeColor"
        />
      </template>
    </svg>
    <div
      v-if="shapeLabelShow"
      class="maps-presentation-element-view__shape-label"
      :style="shapeLabelStyle"
    >
      {{ shapeLabelText }}
    </div>
  </template>

  <div
    v-else-if="element.kind === 'text'"
    ref="textRef"
    class="maps-presentation-element-view__text"
    :class="{ 'maps-presentation-element-view__text--editing': editingText }"
    :contenteditable="editingText"
    :style="textStyle"
    @blur="onTextBlur"
    @keydown.stop
    @pointerdown="editingText && $event.stopPropagation()"
  >
    {{ element.text }}
  </div>

  <div v-else-if="element.kind === 'image'" class="maps-presentation-element-view__image">
    <img v-if="element.src" :src="imageSrc" :alt="element.alt ?? ''" :style="imageStyle" />
    <div v-else class="maps-presentation-element-view__image-empty">
      <span>{{ _t('No image') }}</span>
    </div>
  </div>

  <!-- Group: only a faint bounds hint while editing -->
  <div v-else-if="element.kind === 'group'" class="maps-presentation-element-view__group" />

  <div
    v-else
    class="maps-presentation-element-view__data"
    :style="dataBoxStyle"
    :class="{ 'maps-presentation-element-view__data--unbound': !isBoundElement(element) }"
  >
    <div class="maps-presentation-element-view__data-body">
      <GadgetRenderer
        v-if="element.display.mode === 'gadget' && (isBoundElement(element) || sampleState)"
        :type="effectiveGadgetType"
        :metric="element.display.gadget_metric ?? sampleMetric"
        :state="effectiveState"
        :size="gadgetSize"
        :perfometer="perfometer"
        :metric-units="metricUnits"
      />
      <div
        v-else-if="element.display.mode === 'text'"
        class="maps-presentation-element-view__data-text"
        :style="{ color: stateClr }"
      >
        {{ stateText }}
      </div>
      <img
        v-else-if="element.display.image"
        class="maps-presentation-element-view__data-img"
        :src="resolveImageRef(element.display.image)"
        :alt="''"
        :style="{
          width: `${iconSize}px`,
          height: `${iconSize}px`,
          filter: `drop-shadow(0 0 ${Math.max(2, iconSize * 0.12)}px ${stateClr})`
        }"
      />
      <div
        v-else
        class="maps-presentation-element-view__data-icon"
        :style="{
          width: `${iconSize}px`,
          height: `${iconSize}px`,
          background: stateClr,
          boxShadow: `0 0 ${iconSize * 0.5}px 1px ${stateClr}66`
        }"
      />
    </div>
    <div v-if="showLabel" class="maps-presentation-element-view__data-label" :style="labelStyle">
      {{ labelText }}
    </div>
    <div
      v-if="sampleState && !isBoundElement(element)"
      class="maps-presentation-element-view__sample"
    >
      {{ _t('Sample') }}
    </div>
  </div>
</template>

<style scoped>
.maps-presentation-element-view__svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

/* Centered state label for a bound shape. Lines are only a few px tall, so it
   overflows the box (visible) and sits readably on top via its pill. */
.maps-presentation-element-view__shape-label {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  padding: 1px 6px;
  border-radius: 6px;
  line-height: 1.2;
  white-space: nowrap;
  pointer-events: none;
}

.maps-presentation-element-view__text {
  width: 100%;
  height: 100%;
  outline: none;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.maps-presentation-element-view__text--editing {
  cursor: text;
  box-shadow: 0 0 0 1px var(--pres-accent);
}

.maps-presentation-element-view__image,
.maps-presentation-element-view__image img {
  width: 100%;
  height: 100%;
}

.maps-presentation-element-view__image img {
  display: block;
}

.maps-presentation-element-view__image-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--pres-muted);
  color: var(--pres-muted);
  font-size: 13px;
}

.maps-presentation-element-view__group {
  width: 100%;
  height: 100%;
}

.maps-presentation-element-view__data {
  width: 100%;
  height: 100%;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  overflow: hidden;
}

.maps-presentation-element-view__data--unbound {
  opacity: 0.7;
  border-style: dashed !important;
}

.maps-presentation-element-view__data-body {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;

  /* The gadget inside has a computed pixel size, so a card too small for it
     would otherwise let it spill over the label below. */
  overflow: hidden;
}

.maps-presentation-element-view__data-icon {
  width: 36px;
  height: 36px;
  border-radius: 9999px;
}

.maps-presentation-element-view__data-img {
  object-fit: contain;
}

.maps-presentation-element-view__data-text {
  font-weight: var(--font-weight-bold);
  font-size: 20px;
}

.maps-presentation-element-view__data-label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  /* The caption keeps its line; the gadget above it is what gives way. */
  flex-shrink: 0;
}

/* Editor-only badge marking a slot that previews with sample data. */
.maps-presentation-element-view__sample {
  position: absolute;
  top: 4px;
  right: 6px;
  padding: 0 5px;
  border: 1px dashed var(--pres-muted);
  border-radius: 5px;
  font-size: var(--font-size-small);
  font-family: var(--pres-font, sans-serif);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--pres-muted);
  pointer-events: none;
}
</style>
