<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The slide itself: the stage everything is drawn on, and the editor's surfaces
around it.

A presentation map is the one map type an operator designs rather than
arranges, so this is a small design tool. The behaviour lives in composables --
the document and its history, the selection, the pointer gestures, the
keyboard, the connect walkthrough -- and the toolbars are components of their
own; what stays here is the drawing and the wiring between them.

Outside the editor the same slide is a picture with live status on it, and its
bound elements become drill-down targets like any other map object.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import MapMarqueeBox from '@/maps/map/components/MapMarqueeBox.vue'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import type {
  MapConfig,
  MapElement,
  ObjectState,
  PresentationElement,
  ShapeElement
} from '@/maps/types/api'

import { isBindable, isUnboundSlot } from '../binding'
import { useBindingDrop } from '../composables/useBindingDrop'
import { useCanvasDrag } from '../composables/useCanvasDrag'
import { useCanvasSelection } from '../composables/useCanvasSelection'
import { useCanvasShortcuts } from '../composables/useCanvasShortcuts'
import { useConnectWalkthrough } from '../composables/useConnectWalkthrough'
import { useElementDrillDown } from '../composables/useElementDrillDown'
import { useSelectionGeometry } from '../composables/useSelectionGeometry'
import { useSlideDocument } from '../composables/useSlideDocument'
import { useSlideEditing } from '../composables/useSlideEditing'
import { useSlideSettings } from '../composables/useSlideSettings'
import { useSlideViewport } from '../composables/useSlideViewport'
import { useTemplateGallery } from '../composables/useTemplateGallery'
import { connectorEndpoints, isConnectorShape, isDocked } from '../connectors'
import { elementLabel, imageRefName, resolveImageRef } from '../elements'
import type { Box } from '../geometry'
import { sampleStateFor } from '../sampleState'
import { themeTokens } from '../themes'
import PresentationAlignBar from './PresentationAlignBar.vue'
import PresentationConnectBar from './PresentationConnectBar.vue'
import PresentationConnectOverlay from './PresentationConnectOverlay.vue'
import PresentationConnectPopover from './PresentationConnectPopover.vue'
import PresentationConnector from './PresentationConnector.vue'
import PresentationConnectorLabels from './PresentationConnectorLabels.vue'
import PresentationDataPanel from './PresentationDataPanel.vue'
import PresentationElementView from './PresentationElementView.vue'
import PresentationHistoryBar from './PresentationHistoryBar.vue'
import PresentationInspectorPanel from './PresentationInspectorPanel.vue'
import PresentationLayersPanel from './PresentationLayersPanel.vue'
import PresentationPalette from './PresentationPalette.vue'
import PresentationTemplateGallery from './PresentationTemplateGallery.vue'

const { _t } = usei18n()

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  editMode: boolean
  readonly?: boolean
  preview?: boolean
  kiosk?: boolean
}>()

const emit = defineEmits<{
  'object-hover': [obj: MapElement, event: MouseEvent]
  'object-hover-leave': []
  'object-click': [obj: MapElement, event: MouseEvent | undefined]
  'object-context': [obj: MapElement, event: MouseEvent]
}>()

/** True only where the slide is designed, not merely displayed. */
const interactive = computed(
  () => props.editMode && !props.readonly && !props.preview && !props.kiosk
)

const doc = useSlideDocument(
  () => props.config,
  () => selection.clear()
)
const { local, elements, byId, topLevelId, isGrouped, isHidden, isLocked, history, saveLabel } = doc

const containerRef = ref<HTMLElement | null>(null)
const slideW = computed(() => local.value.width)
const slideH = computed(() => local.value.height)
const { scale, offsetX, offsetY, screenToSlide } = useSlideViewport(containerRef, slideW, slideH)

const selection = useCanvasSelection({ elements, byId, topLevelId, isGrouped, isLocked })
const { selectedIds, selectedIdSet, selectedElements, editingTextId, hasLocked } = selection

const { selectionBox, singleIsConnector, selBoxStyle, handleStyles, rotateHandleStyle } =
  useSelectionGeometry({ selectedElements, scale, byId })

const drag = useCanvasDrag({
  elements,
  byId,
  isGrouped,
  selection,
  screenToSlide,
  snapshot: doc.snapshot,
  scheduleSave: doc.scheduleSave
})

const { marquee, activeGuides } = drag

const editing = useSlideEditing({
  view: local,
  elements,
  byId,
  isLocked,
  nextZ: doc.nextZ,
  selection,
  selectionBox,
  historyVersion: history.version,
  mutate: doc.mutate,
  setElements: doc.setElements,
  snapshot: doc.snapshot,
  scheduleSave: doc.scheduleSave
})

const { canDistribute } = editing

const slide = useSlideSettings({ view: local, elements, byId, scheduleSave: doc.scheduleSave })

const connect = useConnectWalkthrough({
  elements,
  byId,
  viewport: containerRef,
  scale,
  offsetX,
  offsetY
})
const {
  active: connecting,
  current: currentSlot,
  currentBound,
  currentId: currentSlotId,
  boundCount,
  totalCount,
  unboundCount,
  slotBoxes,
  slotTitle,
  metricElement,
  popoverStyle
} = connect

const {
  open: galleryOpen,
  pending: pendingTemplate,
  apply: applyTemplate,
  confirmPending,
  dismiss: dismissGallery
} = useTemplateGallery({
  interactive,
  elementCount: () => elements.value.length,
  mapName: () => props.config.name,
  applyToSlide: (template) => {
    editing.applyTemplate(template)
    connect.enter()
  }
})

/** Effective connection of a bindable element: its own override or the map's. */
function connectionFor(el: PresentationElement): string | null {
  return (isBindable(el) ? el.connection_id : null) || props.config.connection_id || null
}

function stateFor(el: PresentationElement): ObjectState | undefined {
  // Data elements and monitoring-bound shapes both receive states keyed by id.
  return isBindable(el) ? props.states[el.id] : undefined
}

// Unbound data slots preview with deterministic sample data — editor only, so
// view and kiosk keep rendering unbound elements neutrally. Cached by element:
// the preview only depends on the id, and a fresh object every render would
// re-render every unbound element on every pointer move.
const sampleStates = computed(() => {
  if (!interactive.value) {
    return new Map<string, ObjectState>()
  }
  return new Map(
    elements.value.filter(isUnboundSlot).map((el) => [el.id, sampleStateFor(el)] as const)
  )
})
function sampleFor(el: PresentationElement): ObjectState | undefined {
  return sampleStates.value.get(el.id)
}

const drillDown = useElementDrillDown(
  {
    interactive,
    preview: () => !!props.preview,
    connectionFor,
    stateFor
  },
  emit
)

const bindingDrop = useBindingDrop({
  interactive,
  view: local,
  elements,
  byId,
  nextZ: doc.nextZ,
  selection,
  screenToSlide,
  add: editing.add,
  patch: editing.patchElement
})

// One highlight, two gestures that offer it: a connector endpoint looking for
// something to dock to, and a binding dragged in from the data browser.
const highlightedTarget = computed<Box | null>(() => {
  const el = byId(drag.dockCandidateId.value ?? bindingDrop.targetId.value ?? undefined)
  return el ? { x: el.x, y: el.y, w: el.w, h: el.h } : null
})

useCanvasShortcuts({
  interactive,
  editingText: () => !!editingTextId.value,
  hasSelection: () => selectedIds.value.length > 0,
  connecting: () => connecting.value,
  actions: {
    undo: doc.undo,
    redo: doc.redo,
    copy: editing.copy,
    paste: editing.paste,
    duplicate: editing.duplicate,
    remove: editing.remove,
    nudge: editing.nudge,
    endTextEdit: () => {
      editingTextId.value = null
    },
    leaveConnect: connect.exit,
    clearSelection: selection.clear
  }
})

const themeVars = computed(() => themeTokens(local.value.theme))
const stageStyle = computed(() => ({
  ...themeVars.value,
  position: 'absolute' as const,
  left: `${offsetX.value}px`,
  top: `${offsetY.value}px`,
  width: `${slideW.value}px`,
  height: `${slideH.value}px`,
  transform: `scale(${scale.value})`,
  transformOrigin: 'top left'
}))

// Slide background: an optional image (image-store filename or external URL)
// layered over the chosen color, or the theme's default when unset.
const bgStyle = computed(() => {
  const color = local.value.background || 'var(--pres-bg)'
  const url = resolveImageRef(local.value.background_image)
  if (!url) {
    return { background: color }
  }
  return {
    backgroundColor: color,
    backgroundImage: `url("${url}")`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat'
  }
})
const overlaySvgStyle = computed(() => ({
  width: `${slideW.value}px`,
  height: `${slideH.value}px`
}))
const backgroundImageName = computed(() => imageRefName(local.value.background_image))

const orderedElements = computed(() =>
  [...elements.value].filter((el) => !isHidden(el) || interactive.value).sort((a, b) => a.z - b.z)
)
const layersList = computed(() =>
  [...elements.value].sort((a, b) => b.z - a.z).filter((el) => !isGrouped(el.id))
)

// Every line and arrow renders in a slide-space overlay (any angle) instead of
// inline, so its endpoints can be dragged freely and docked to other elements.
const connectors = computed(() =>
  orderedElements.value
    .filter((el): el is ShapeElement => isConnectorShape(el))
    .map((el) => ({ el, ...connectorEndpoints(el, byId) }))
)
const inlineElements = computed(() => orderedElements.value.filter((el) => !isConnectorShape(el)))
// What a connector endpoint can be docked to, for the inspector's picker. Only
// derived while a connector is selected — labelling every element on the slide
// would otherwise re-run on each keystroke in a name field.
const connectorTargets = computed(() =>
  selectedElements.value.some(isConnectorShape)
    ? elements.value
        .filter((el) => el.kind !== 'group')
        .map((el) => ({ id: el.id, name: elementLabel(_t, el) }))
    : []
)

function elementStyle(el: PresentationElement): Record<string, string> {
  return {
    left: `${el.x}px`,
    top: `${el.y}px`,
    width: `${el.w}px`,
    height: `${el.h}px`,
    opacity: String(el.opacity),
    transform: el.rotation ? `rotate(${el.rotation}deg)` : 'none',
    zIndex: String(el.z),
    // View mode keeps decorative elements transparent to the pointer, but a
    // bound element is a drill-down target (hover card, detail drawer).
    pointerEvents: interactive.value
      ? isLocked(el)
        ? 'none'
        : 'auto'
      : drillDown.isLinked(el)
        ? 'auto'
        : 'none'
  }
}

const layersOpen = ref(false)
const dataPanelOpen = ref(false)

/** In connect mode a click only retargets the walkthrough to an unbound slot. */
function retargetGuide(el: PresentationElement): void {
  if (isUnboundSlot(el)) {
    connect.goTo(el.id)
  }
}

function onStagePointerDown(e: PointerEvent): void {
  if (!interactive.value || connecting.value) {
    return
  }
  editingTextId.value = null
  // A pointer-down on the bare canvas gutter (the area around the slide, not an
  // element, panel or toolbar — those stop propagation or are child nodes)
  // deselects, which closes the inspector. Without this, only clicks that land
  // on the slide itself would dismiss it.
  if (e.target === containerRef.value) {
    selection.clear()
  }
}

function onSlidePointerDown(e: PointerEvent): void {
  if (!interactive.value || connecting.value) {
    return
  }
  // A click on the slide ends any in-progress text edit (the contenteditable's
  // blur commits it) and clears the selection, dismissing the inspector. The
  // element being edited swallows its own pointer events, so reaching here
  // always means the click landed outside it.
  selection.clear()
  drag.beginMarquee(screenToSlide(e.clientX, e.clientY), e.shiftKey, e)
}

function onElementPointerDown(el: PresentationElement, e: PointerEvent): void {
  if (!interactive.value || isLocked(el)) {
    return
  }
  if (connecting.value) {
    retargetGuide(el)
    return
  }
  selection.pick(el, e.shiftKey)
  drag.beginMove(topLevelId(el.id), e)
}

// A connector lives in the overlay, not the inline element layer, so it gets
// its own handler. Propagation stops so the stage's deselect doesn't fire. A
// connector with neither end docked can still be dragged by its body.
function onConnectorPointerDown(el: ShapeElement, e: PointerEvent): void {
  if (!interactive.value || isLocked(el)) {
    return
  }
  e.stopPropagation()
  if (connecting.value) {
    retargetGuide(el)
    return
  }
  selection.select(el.id)
  if (!isDocked(el, byId)) {
    drag.beginMove(el.id, e)
  }
}

function onEndpointPointerDown(el: ShapeElement, which: 'start' | 'end', e: PointerEvent): void {
  if (!interactive.value || isLocked(el)) {
    return
  }
  e.stopPropagation()
  selection.select(el.id)
  drag.beginEndpoint(el, which, e)
}

function onSlideDblClick(e: MouseEvent): void {
  if (!interactive.value) {
    return
  }
  const p = screenToSlide(e.clientX, e.clientY)
  const hit = [...orderedElements.value]
    .reverse()
    .find((el) => p.x >= el.x && p.x <= el.x + el.w && p.y >= el.y && p.y <= el.y + el.h)
  if (hit?.kind === 'text') {
    selection.select(hit.id)
    editingTextId.value = hit.id
  }
}

function enterConnectMode(): void {
  selection.clear()
  connect.enter()
}

function patchCurrentSlot(patch: Record<string, unknown>): void {
  const el = currentSlot.value
  if (el) {
    editing.patchElement(el, patch)
  }
}
</script>

<template>
  <div class="maps-presentation-canvas" :class="{ 'maps-presentation-canvas--edit': interactive }">
    <PresentationDataPanel
      v-if="interactive && dataPanelOpen"
      :connection-id="config.connection_id"
      :elements="elements"
      :states="states"
      @close="dataPanelOpen = false"
    />
    <div
      ref="containerRef"
      class="maps-presentation-canvas__viewport"
      @pointerdown="onStagePointerDown"
      @dragover="bindingDrop.onDragOver"
      @dragleave="bindingDrop.onDragLeave"
      @drop="bindingDrop.onDrop"
    >
      <div
        class="maps-presentation-canvas__stage"
        :style="stageStyle"
        @pointerdown.stop="onSlidePointerDown"
        @dblclick="onSlideDblClick"
      >
        <div class="maps-presentation-canvas__bg" :style="bgStyle" />

        <!-- Connectors render in their own slide-space layer (behind boxes) so a
           docked line can run at any angle between the elements it links. -->
        <svg class="maps-presentation-canvas__connectors" :style="overlaySvgStyle">
          <!-- Highlight the element an endpoint would dock to on release. -->
          <rect
            v-if="highlightedTarget"
            class="maps-presentation-canvas__dock-target"
            :x="highlightedTarget.x"
            :y="highlightedTarget.y"
            :width="highlightedTarget.w"
            :height="highlightedTarget.h"
            :stroke-width="2 / scale"
            :rx="6 / scale"
          />
          <PresentationConnector
            v-for="c in connectors"
            :key="c.el.id"
            :element="c.el"
            :start="c.start"
            :end="c.end"
            :state="stateFor(c.el) ?? sampleFor(c.el)"
            :selected="interactive && selectedIdSet.has(c.el.id)"
            :interactive="interactive"
            :hoverable="drillDown.isLinked(c.el)"
            :scale="scale"
            @pointerdown="onConnectorPointerDown(c.el, $event)"
            @endpoint-down="(which, e) => onEndpointPointerDown(c.el, which, e)"
            @hover="drillDown.onHoverEnter(c.el, $event)"
            @hover-leave="drillDown.onHoverLeave(c.el)"
            @open="drillDown.onClick(c.el, $event)"
            @context="drillDown.onContextMenu(c.el, $event)"
          />
        </svg>

        <div v-if="interactive && !elements.length" class="maps-presentation-canvas__empty">
          {{ _t('Pick a tool above to start your slide') }}
        </div>

        <!-- Isolated stacking context: element z values (unbounded via
           bring-to-front) order elements among themselves but can never climb
           above the later overlays — DOM order alone keeps pills, selection
           and badges on top. -->
        <div class="maps-presentation-canvas__els">
          <div
            v-for="el in inlineElements"
            :key="el.id"
            class="maps-presentation-canvas__el"
            :class="{
              'maps-presentation-canvas__el--selected':
                interactive && selectedIdSet.has(topLevelId(el.id)),
              'maps-presentation-canvas__el--locked': isLocked(el),
              'maps-presentation-canvas__el--hidden': interactive && isHidden(el),
              'maps-presentation-canvas__el--link': drillDown.isLinked(el)
            }"
            :style="elementStyle(el)"
            :tabindex="drillDown.isLinked(el) ? 0 : undefined"
            :role="drillDown.isLinked(el) ? 'button' : undefined"
            :aria-label="drillDown.ariaLabel(el)"
            @pointerdown.stop="onElementPointerDown(el, $event)"
            @mouseenter="drillDown.onHoverEnter(el, $event)"
            @mouseleave="drillDown.onHoverLeave(el)"
            @click="drillDown.onClick(el, $event)"
            @keydown="drillDown.onKeydown(el, $event)"
            @contextmenu="drillDown.onContextMenu(el, $event)"
          >
            <PresentationElementView
              :element="el"
              :state="stateFor(el)"
              :connection-id="connectionFor(el)"
              :sample-state="sampleFor(el)"
              :editing-text="editingTextId === el.id"
              @text-change="editing.setText(el.id, $event)"
            />
          </div>
        </div>

        <!-- Connector value pills above the elements — a docked endpoint sits
           under its element, which would otherwise cover the label. -->
        <svg class="maps-presentation-canvas__connectors" :style="overlaySvgStyle">
          <PresentationConnectorLabels
            v-for="c in connectors"
            :key="`lbl-${c.el.id}`"
            :element="c.el"
            :start="c.start"
            :end="c.end"
            :state="stateFor(c.el) ?? sampleFor(c.el)"
            :connection-id="connectionFor(c.el)"
          />
        </svg>

        <svg
          v-if="interactive && activeGuides.length"
          class="maps-presentation-canvas__guides"
          :style="overlaySvgStyle"
        >
          <line
            v-for="(g, i) in activeGuides"
            :key="i"
            :x1="g.axis === 'x' ? g.pos : g.start"
            :y1="g.axis === 'x' ? g.start : g.pos"
            :x2="g.axis === 'x' ? g.pos : g.end"
            :y2="g.axis === 'x' ? g.end : g.pos"
            :stroke-width="1 / scale"
          />
        </svg>

        <div
          v-if="interactive && selectionBox"
          class="maps-presentation-canvas__sel"
          :style="selBoxStyle"
        >
          <template v-if="selectedIds.length === 1 && !hasLocked && !singleIsConnector">
            <div
              v-for="(style, handle) in handleStyles"
              :key="handle"
              class="maps-presentation-canvas__handle"
              :class="`maps-presentation-canvas__handle--${handle}`"
              :style="style"
              @pointerdown.stop="drag.beginTransform('resize', handle, $event)"
            />
            <div
              class="maps-presentation-canvas__rotate"
              :style="rotateHandleStyle"
              @pointerdown.stop="drag.beginTransform('rotate', '', $event)"
            />
          </template>
        </div>

        <MapMarqueeBox v-if="marquee.visible.value" :rect="marquee.rect.value" :layer="1001" />

        <PresentationConnectOverlay
          v-if="interactive && connecting"
          :slots="slotBoxes"
          :current-id="currentSlotId"
          :scale="scale"
          @pick="connect.goTo($event)"
        />
      </div>

      <PresentationTemplateGallery
        v-if="interactive && galleryOpen"
        @apply="applyTemplate"
        @close="dismissGallery"
      />

      <MapsConfirmDialog
        :open="!!pendingTemplate"
        :title="_t('Replace slide contents?')"
        :message="
          _t('Applying a template replaces every element on this slide. Undo restores them.')
        "
        :confirm-label="_t('Apply template')"
        @confirm="confirmPending"
        @cancel="pendingTemplate = null"
      />

      <PresentationConnectBar
        v-if="interactive && connecting"
        :bound="boundCount"
        :total="totalCount"
        @previous="connect.prev()"
        @next="connect.next()"
        @done="connect.exit()"
      />

      <PresentationConnectPopover
        v-if="interactive && connecting && currentSlot"
        :ref="connect.setPopover"
        :element="currentSlot"
        :connection-id="config.connection_id"
        :title="slotTitle"
        :bound="currentBound"
        :metric-element="metricElement"
        :remaining="unboundCount"
        :position="popoverStyle"
        @patch="patchCurrentSlot"
        @next="connect.next()"
        @done="connect.exit()"
      />

      <PresentationPalette
        v-if="interactive && !connecting"
        :data-panel-open="dataPanelOpen"
        :layers-open="layersOpen"
        :unbound-count="unboundCount"
        @insert="editing.insert"
        @connect="enterConnectMode"
        @toggle-data-panel="dataPanelOpen = !dataPanelOpen"
        @toggle-layers="layersOpen = !layersOpen"
      />

      <PresentationHistoryBar
        v-if="interactive"
        :can-undo="history.canUndo.value"
        :can-redo="history.canRedo.value"
        @undo="doc.undo"
        @redo="doc.redo"
      />

      <PresentationAlignBar
        v-if="interactive && selectedIds.length >= 2 && !connecting"
        :can-distribute="canDistribute"
        @align="editing.align"
        @distribute="editing.distribute"
      />

      <PresentationLayersPanel
        v-if="interactive && layersOpen"
        :elements="layersList"
        :selected-ids="selectedIds"
        @pick="(id, extend) => (extend ? selection.toggle(id) : selection.select(id))"
        @toggle-lock="editing.toggleLock"
        @toggle-hidden="editing.toggleHidden"
        @group="editing.group"
        @ungroup="editing.ungroup"
        @close="layersOpen = false"
      />
    </div>

    <PresentationInspectorPanel
      v-if="interactive"
      :selection="selectedElements"
      :view="local"
      :connection-id="config.connection_id"
      :targets="connectorTargets"
      :background-image-name="backgroundImageName"
      :save-label="saveLabel"
      @patch="editing.patchSelection"
      @delete="editing.remove"
      @duplicate="editing.duplicate"
      @slide="slide.change"
      @save="doc.saveNow"
      @group="editing.group"
      @ungroup="editing.ungroup"
      @browse-templates="galleryOpen = true"
    />
  </div>
</template>

<style scoped>
.maps-presentation-canvas {
  display: flex;
  align-items: stretch;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--ux-theme-1);
}

/* The checkerboard gutter is editor chrome — view/kiosk get a calm surround. */
.maps-presentation-canvas--edit {
  background:
    repeating-conic-gradient(rgb(128 128 128 / 7%) 0% 25%, transparent 0% 50%) 50% / 22px 22px,
    var(--ux-theme-1);
}

/* The slide viewport flexes between the docked panels; useSlideViewport's
   ResizeObserver re-fits the zoom whenever a panel opens or closes. */
.maps-presentation-canvas__viewport {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.maps-presentation-canvas__stage {
  box-shadow: 0 12px 48px rgb(0 0 0 / 50%);
  user-select: none;
}

.maps-presentation-canvas__bg {
  position: absolute;
  inset: 0;
}

.maps-presentation-canvas__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pres-muted);
  font-family: var(--pres-font);
  font-size: 28px;
  letter-spacing: 0.02em;
  pointer-events: none;
}

.maps-presentation-canvas__el {
  position: absolute;
  transform-origin: center center;
}

.maps-presentation-canvas__el--selected {
  cursor: move;
}

.maps-presentation-canvas__el--link {
  cursor: pointer;
}

.maps-presentation-canvas__el--link:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-presentation-canvas__el--locked {
  cursor: default;
}

/* Hidden elements stay visible while editing (so they remain reachable) but
   dimmed + checkered, making a Hide toggle visibly take effect. They vanish
   entirely outside edit mode via the orderedElements filter. */
.maps-presentation-canvas__el--hidden {
  opacity: 0.3 !important;
}

.maps-presentation-canvas__guides {
  position: absolute;
  z-index: 1001;
  inset: 0;
  pointer-events: none;
  overflow: visible;
  stroke: var(--color-pink-40);
}

/* Connector layer sits above the background but below the element boxes. The
   svg itself ignores pointer events; each connector re-enables them on its own
   hit line, so clicks elsewhere fall through to the stage. */
.maps-presentation-canvas__connectors {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

/* Container for all slide elements. isolation: isolate keeps their z-index
   values local, so overlays later in the DOM (value pills, selection, badges)
   always paint above without any magic z numbers. pointer-events: none lets
   stage clicks through; each element re-enables its own via elementStyle. */
.maps-presentation-canvas__els {
  position: absolute;
  inset: 0;
  isolation: isolate;
  pointer-events: none;
}

.maps-presentation-canvas__dock-target {
  fill: color-mix(in srgb, var(--color-corporate-green-50) 14%, transparent);
  stroke: var(--color-corporate-green-50);
  pointer-events: none;
}

/* The selection box sits above every element (template z reaches 40+) so the
   resize/rotate handles stay clickable; the box itself ignores pointers. */
.maps-presentation-canvas__sel {
  position: absolute;
  z-index: 1000;
  outline: solid var(--color-corporate-green-50);
  pointer-events: none;
}

.maps-presentation-canvas__handle {
  position: absolute;
  background: rgb(255 255 255);
  border: solid var(--color-corporate-green-50);
  border-radius: var(--border-radius-half);
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%);
  pointer-events: auto;
}

.maps-presentation-canvas__handle--nw,
.maps-presentation-canvas__handle--se {
  cursor: nwse-resize;
}

.maps-presentation-canvas__handle--ne,
.maps-presentation-canvas__handle--sw {
  cursor: nesw-resize;
}

.maps-presentation-canvas__handle--n,
.maps-presentation-canvas__handle--s {
  cursor: ns-resize;
}

.maps-presentation-canvas__handle--e,
.maps-presentation-canvas__handle--w {
  cursor: ew-resize;
}

.maps-presentation-canvas__rotate {
  position: absolute;
  background: rgb(255 255 255);
  border: solid var(--color-corporate-green-50);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%);
  cursor: grab;
  pointer-events: auto;
}
</style>
