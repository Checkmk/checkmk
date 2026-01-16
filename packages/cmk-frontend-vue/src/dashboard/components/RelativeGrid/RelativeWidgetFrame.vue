<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'

import DashboardContent from '@/dashboard/components/DashboardContent/DashboardContent.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import MissingFiltersMsg from '@/dashboard/components/DashboardFilterSettings/MissingFiltersMsg.vue'

import type { ResizeDirection } from './helpers/resizeHelper.ts'
import { ANCHOR_POSITION, type DimensionModes, SIZING_MODE } from './types'

const { _t } = usei18n()

const props = defineProps<{
  debug?: boolean
  isEditing: boolean
  contentProps: ContentProps
  isResizable: boolean
  dimensions: { width: number; height: number }
  position: { left: number; top: number }
  zIndex: number
  anchorPosition: ANCHOR_POSITION
  dimensionModes: DimensionModes
  handleDrag: (e: PointerEvent) => void
  handleResize: (e: PointerEvent, direction: ResizeDirection) => void
}>()

const emit = defineEmits<{
  (e: 'click:edit'): void
  (e: 'click:clone'): void
  (e: 'click:delete'): void
  (e: 'toggle:sizing', dimension: 'width' | 'height'): void
  (e: 'update:anchorPosition', position: ANCHOR_POSITION): void
}>()

const containerStyle = computed(() => ({
  top: `${props.position?.top || 0}px`,
  left: `${props.position?.left || 0}px`,
  width: `${props.dimensions?.width || 100}px`,
  height: `${props.dimensions?.height || 100}px`
}))

const anchorBackgroundColorClass = (pos: string) =>
  props.anchorPosition === pos ? 'anchor-icon--selected' : 'anchor-icon--unselected'

const getSizingText = (mode: SIZING_MODE | undefined, dimension: 'width' | 'height'): string => {
  if (!mode) {
    return `Manual ${dimension}`
  }
  switch (mode) {
    case SIZING_MODE.MAX:
      return `Max ${dimension}`
    case SIZING_MODE.GROW:
      return `Auto ${dimension}`
    case SIZING_MODE.MANUAL:
    default:
      return `Manual ${dimension}`
  }
}

const anchorCorners = [
  { key: 'tl', pos: ANCHOR_POSITION.TOP_LEFT },
  { key: 'tr', pos: ANCHOR_POSITION.TOP_RIGHT },
  { key: 'bl', pos: ANCHOR_POSITION.BOTTOM_LEFT },
  { key: 'br', pos: ANCHOR_POSITION.BOTTOM_RIGHT }
]

function onAnchorSelect(pos: ANCHOR_POSITION) {
  emit('update:anchorPosition', pos)
}
</script>

<template>
  <div
    :id="`db-relative-grid-frame-${contentProps.widget_id}`"
    class="db-relative-grid-frame db-widget-theme"
    :style="{ ...containerStyle }"
    :aria-label="_t('Widget')"
  >
    <MissingFiltersMsg>
      <div :style="{ position: 'relative', height: '100%', width: '100%', zIndex: zIndex }">
        <DashboardContent v-bind="contentProps" />

        <div
          v-if="props.isEditing"
          :id="`dashlet_controls_${contentProps!.widget_id}`"
          class="controls"
          @pointerdown="handleDrag"
        >
          <!-- Resize handles -->
          <div
            v-if="isResizable && props.dimensionModes.width === SIZING_MODE.MANUAL"
            class="resize-handle resize-left resize"
            @pointerdown.stop.prevent="(e) => handleResize(e, 'left')"
          ></div>
          <div
            v-if="isResizable && props.dimensionModes.width === SIZING_MODE.MANUAL"
            class="resize-handle resize-right resize-right-border"
            @pointerdown.stop.prevent="(e) => handleResize(e, 'right')"
          ></div>
          <div
            v-if="isResizable && props.dimensionModes.height === SIZING_MODE.MANUAL"
            class="resize-handle resize-top resize-top-border"
            @pointerdown.stop.prevent="(e) => handleResize(e, 'top')"
          ></div>
          <div
            v-if="isResizable && props.dimensionModes.height === SIZING_MODE.MANUAL"
            class="resize-handle resize-bottom resize-bottom-border"
            @pointerdown.stop.prevent="(e) => handleResize(e, 'bottom')"
          ></div>

          <!-- Anchors -->
          <template v-for="corner in anchorCorners" :key="corner.key">
            <div class="anchor-slot" :class="`anchor--${corner.key}`">
              <div
                :class="`anchor-icon ${anchorBackgroundColorClass(corner.pos)}`"
                aria-hidden="true"
                @pointerdown.stop.prevent="onAnchorSelect(corner.pos)"
              />
              <div
                v-if="props.anchorPosition === corner.pos"
                class="anchor-label anchor-label-pos anchor-label-color"
              >
                {{ _t('Anchor') }}
              </div>
            </div>
          </template>

          <!-- Centered edit controls -->
          <div class="db-centered-edit-controls">
            <!-- left column: sizing buttons -->
            <div v-if="isResizable" class="db-sizing-controls">
              <CmkButton
                class="sizing-button"
                :title="_t('Toggle sizing for width')"
                @click.stop="emit('toggle:sizing', 'width')"
              >
                {{ getSizingText(props.dimensionModes.width, 'width') }}
              </CmkButton>

              <CmkButton
                class="sizing-button"
                :title="_t('Toggle sizing for height')"
                @click.stop="emit('toggle:sizing', 'height')"
              >
                {{ getSizingText(props.dimensionModes.height, 'height') }}
              </CmkButton>
            </div>

            <!-- right row: icon buttons -->
            <div class="db-icon-controls">
              <CmkIconButton
                class="db-centered-edit-controls-button control-button-color"
                name="widget-delete"
                size="xlarge"
                :aria-label="_t('Delete widget')"
                @click="emit('click:delete')"
              />
              <CmkIconButton
                class="db-centered-edit-controls-button control-button-color"
                name="widget-clone"
                size="xlarge"
                :aria-label="_t('Clone widget')"
                @click="emit('click:clone')"
              />
              <CmkIconButton
                class="db-centered-edit-controls-button control-button-color"
                name="widget-edit"
                size="xlarge"
                :aria-label="_t('Edit widget')"
                @click="emit('click:edit')"
              />
            </div>
          </div>

          <!-- Debug info -->
          <div v-if="debug" class="debug-container">
            {{ dimensions.width }} x {{ dimensions.height }} | {{ position.left }},{{
              position.top
            }}
          </div>
        </div>
      </div>
    </MissingFiltersMsg>
  </div>
</template>

<style scoped>
/* Not applying the dimension variables because this is unique to the relative grid implementation */

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='facelift'] .db-widget-theme {
  --resize-border-color: var(--color-corporate-green-80);

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-label-color {
    color: var(--color-corporate-green-80);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-icon--selected {
    background-color: var(--color-corporate-green-50);
    border: 1px solid var(--color-corporate-green-80);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-icon--unselected {
    background-color: var(--color-mid-grey-50);
    border: 1px solid var(--color-mid-grey-50);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .control-button-color {
    filter: brightness(0) saturate(100%) invert(100%) sepia(0%) saturate(7500%) hue-rotate(93deg)
      brightness(0%) contrast(105%);
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-widget-theme {
  --resize-border-color: var(--color-corporate-green-50);

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-label-color {
    color: var(--color-corporate-green-50);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-icon--selected {
    background-color: var(--color-corporate-green-50);
    border: 1px solid var(--color-corporate-green-50);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .anchor-icon--unselected {
    background-color: var(--color-mid-grey-60);
    border: 1px solid var(--color-mid-grey-60);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .control-button-color {
    filter: brightness(0) saturate(100%) invert(100%) sepia(0%) saturate(7500%) hue-rotate(93deg)
      brightness(105%) contrast(105%);
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-relative-grid-frame {
  --anchor-size: var(--dimension-5);

  position: absolute;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: var(--dimension-3);
  box-sizing: border-box;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.controls {
  position: absolute;
  top: 0;
  left: 0;
  isolation: isolate;
  width: 100%;
  height: 100%;
  z-index: 1000;
  cursor: auto;
  background-color: rgb(from var(--ux-theme-4) r g b / 80%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-handle {
  position: absolute;
  z-index: 1100;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-left {
  top: 0;
  left: 0;
  width: 6px;
  height: 100%;
  border-left: var(--dimension-1) dashed var(--resize-border-color);
  cursor: ew-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-right {
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  border-right: var(--dimension-1) dashed var(--resize-border-color);
  cursor: ew-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-top {
  top: 0;
  left: 0;
  width: 100%;
  height: 6px;
  border-top: var(--dimension-1) dashed var(--resize-border-color);
  cursor: ns-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.resize-bottom {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 6px;
  border-bottom: var(--dimension-1) dashed var(--resize-border-color);
  cursor: ns-resize;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-slot {
  position: absolute;
  z-index: 1101;
  pointer-events: none; /* prevents stray pointer hits on the slot itself */
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-icon {
  width: var(--anchor-size);
  height: var(--anchor-size);
  border: 1px solid rgb(from var(--black) r g b / 15%);
  pointer-events: auto; /* re-enable on the actual target */
  cursor: pointer;
  clip-path: polygon(0 0, 100% 0, 0 100%); /* default TL shape */
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-label {
  position: absolute;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--tl {
  top: 0;
  left: 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(0 0, 100% 0, 0 100%);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    top: 6px;
    left: 12px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--tr {
  top: 0;
  right: 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(100% 0, 100% 100%, 0 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    top: 6px;
    right: 12px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--bl {
  left: 0;
  bottom: 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(0 100%, 100% 100%, 0 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    bottom: 6px;
    left: 12px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor--br {
  bottom: 0;
  right: 0;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-icon {
    clip-path: polygon(100% 100%, 0 100%, 100% 0);
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  & .anchor-label-pos {
    bottom: 6px;
    right: 12px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.anchor-icon:hover {
  filter: brightness(1.15);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transform: translate(-50%, -50%);
  z-index: 1200;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-sizing-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-icon-controls {
  display: flex;
  flex-direction: row;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls-button {
  padding: 6px 8px;
  transition: filter 200ms ease;
  border: none;
  background-color: transparent;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.db-centered-edit-controls-button:hover {
  filter: brightness(0) saturate(100%) invert(39%) sepia(98%) saturate(749%) hue-rotate(85deg)
    brightness(91%) contrast(86%);
  background-color: rgb(from var(--ux-theme-5) r g b / 20%);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.sizing-button {
  border: 1px solid var(--ux-theme-10);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.debug-container {
  position: absolute;
  bottom: 4px;
  left: 4px;
  font-size: 10px;
  color: var(--font-color);
  padding: 2px 4px;
  border-radius: 3px;
  pointer-events: none;
  z-index: 2000;
}
</style>
