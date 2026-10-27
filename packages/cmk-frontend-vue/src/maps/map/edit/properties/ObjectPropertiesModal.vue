<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Everything about one object on a map, as a card at the top of the map, on the
side away from the object it edits so it stays in view. The header drags the
card aside. An
edited card asks before any way out of it discards the form: a click beside
it, Escape, the close button or Cancel. Which properties it shows follows from
the object's type — the sections decide that for themselves.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef, watch } from 'vue'

import { useDraggableCard } from '@/maps/map/edit/composables/useDraggableCard'
import { useObjectMetrics } from '@/maps/map/edit/composables/useObjectMetrics'
import { useObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import {
  type GraphSource,
  applyGraphSource,
  graphSourceOf
} from '@/maps/map/edit/properties/graphSource'
import {
  type ObjectForm,
  boundTypeOf,
  formFromObject,
  leavesOutMembers,
  updatesFromForm,
  weatherColorNeedsMetric
} from '@/maps/map/edit/properties/objectForm'
import AppearanceSection from '@/maps/map/edit/properties/sections/AppearanceSection.vue'
import FilterSection from '@/maps/map/edit/properties/sections/FilterSection.vue'
import GraphEmbedSection from '@/maps/map/edit/properties/sections/GraphEmbedSection.vue'
import GraphSourceSection from '@/maps/map/edit/properties/sections/GraphSourceSection.vue'
import IdentitySection from '@/maps/map/edit/properties/sections/IdentitySection.vue'
import LabelSection from '@/maps/map/edit/properties/sections/LabelSection.vue'
import LineSection from '@/maps/map/edit/properties/sections/LineSection.vue'
import LinkSection from '@/maps/map/edit/properties/sections/LinkSection.vue'
import PositionSection from '@/maps/map/edit/properties/sections/PositionSection.vue'
import TemplatesSection from '@/maps/map/edit/properties/sections/TemplatesSection.vue'
import TextboxSection from '@/maps/map/edit/properties/sections/TextboxSection.vue'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import MapsUnsavedChangesDialog from '@/maps/shared/components/MapsUnsavedChangesDialog.vue'
import { useEscapeClose } from '@/maps/shared/composables/useEscapeClose'
import type { MapElement, MapViewType, ObjectState } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'
import { objectDeleteTitle, objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { buildCheckmkViewUrl } from '@/maps/utils/mapNavigation'
import { VISUAL_ONLY_TYPES, getMapElementName } from '@/maps/utils/naming'

const props = defineProps<{
  object: MapElement
  state?: ObjectState | undefined
  connectionId: string
  mapType?: MapViewType | undefined
  mapIconSize?: number | null
  mapDefaultZ?: number
  checkmkUrl?: string | null
  /** Where the object it edits is on screen, for the card to open away from. */
  avoid?: AnchorRect | null
}>()

const emit = defineEmits<{
  close: []
  save: [updates: Record<string, unknown>]
  delete: []
  detach: []
}>()

const { _t } = usei18n()

const form = ref<ObjectForm>(formFromObject(props.object, { z: props.mapDefaultZ ?? 1 }))
const graphSource = ref<GraphSource>(graphSourceOf(props.object))

// What a save would send, so a field cleared back to empty is no edit.
const updates = () => JSON.stringify(updatesFromForm(form.value, props.object, props.mapType))
/** The card as it opened, to tell an edited card from an untouched one. */
const pristine = ref(updates())
const dirty = computed(() => updates() !== pristine.value)

// Another object may be selected while the card is open, so the form follows
// whatever it is showing.
watch(
  () => props.object,
  (object) => {
    form.value = formFromObject(object, { z: props.mapDefaultZ ?? 1 })
    graphSource.value = graphSourceOf(object)
    pristine.value = updates()
  }
)

function setGraphSource(source: GraphSource): void {
  graphSource.value = source
  applyGraphSource(form.value, source)
}

const boundType = computed(() => boundTypeOf(form.value, props.object))

// The per-object connection override wins over the map's own.
const connectionId = computed(() => form.value.connection_id || props.connectionId)

const suggestions = useObjectSuggestions({
  connectionId: () => connectionId.value,
  objectType: () => boundType.value,
  mapName: () => form.value.map_name
})

const metrics = useObjectMetrics({
  object: () => props.object,
  state: () => props.state,
  connectionId: () => connectionId.value,
  hostName: () => form.value.host_name,
  serviceDescription: () => form.value.service_description
})

const frame = useTemplateRef<HTMLElement>('frame')
const { dragOffset, dragging, onHeaderPointerDown, onHeaderPointerMove, onHeaderPointerUp } =
  useDraggableCard(
    () => props.object,
    () => frame.value
  )

const side = ref<'center' | 'left' | 'right'>('center')
let sideChosen = false
// Chosen once per object: a card that moved whenever the object did would jump
// under the pointer. A just-placed object is only measured after the card
// opened, so it waits for the first box.
watch(
  () => [props.object.id, props.avoid] as const,
  ([id, avoid], previous) => {
    if (previous && previous[0] !== id) {
      sideChosen = false
      side.value = 'center'
    }
    if (sideChosen || !avoid) {
      return
    }
    sideChosen = true
    side.value = (avoid.left + avoid.right) / 2 < window.innerWidth / 2 ? 'right' : 'left'
  },
  { immediate: true }
)

const cardStyle = computed(() => {
  const { dx, dy } = dragOffset.value
  return {
    transform:
      side.value === 'center'
        ? `translate(calc(-50% + ${dx}px), ${dy}px)`
        : `translate(${dx}px, ${dy}px)`
  }
})

const confirmDiscard = ref(false)

/** Every way out of the card: an edited one asks before it discards. */
function requestClose(): void {
  if (dirty.value) {
    confirmDiscard.value = true
  } else {
    emit('close')
  }
}

function discard(): void {
  confirmDiscard.value = false
  emit('close')
}

const displayName = computed(() => getMapElementName(props.object) ?? '')

/** The object's own page in Checkmk, offered as the link field's default. */
const autoUrl = computed((): string | null => {
  const options = { site: props.state?.site_id ?? null }
  const type = boundType.value
  if (type === 'host' && form.value.host_name) {
    return buildCheckmkViewUrl(
      props.checkmkUrl,
      'hoststatus',
      { host: form.value.host_name },
      options
    )
  }
  if (type === 'service' && form.value.host_name && form.value.service_description) {
    return buildCheckmkViewUrl(
      props.checkmkUrl,
      'service',
      { host: form.value.host_name, service: form.value.service_description },
      options
    )
  }
  if (type === 'hostgroup' && form.value.group_name) {
    return buildCheckmkViewUrl(
      props.checkmkUrl,
      'hostgroup',
      { hostgroup: form.value.group_name },
      options
    )
  }
  if (type === 'servicegroup' && form.value.group_name) {
    return buildCheckmkViewUrl(
      props.checkmkUrl,
      'servicegroup',
      { servicegroup: form.value.group_name },
      options
    )
  }
  return null
})

const objectType = computed(() => props.object.type)
const isLine = computed(() => objectType.value === 'line')
// A line left without a host stays a plain line, as updatesFromForm stores it.
const stateful = computed(
  () =>
    !VISUAL_ONLY_TYPES.includes(boundType.value) &&
    !(isLine.value && boundType.value === 'host' && !form.value.host_name)
)
const showsIdentity = computed(() => !['textbox', 'graph', 'image'].includes(objectType.value))
const showsAppearance = computed(() => !['line', 'textbox', 'graph'].includes(objectType.value))
const showsFilter = computed(() => leavesOutMembers(boundType.value))

const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)

// Escape on one of the card's own questions answers that question.
useEscapeClose(() => {
  if (!confirmDiscard.value && !confirmDelete.value) {
    requestClose()
  }
})

function save(): void {
  saveError.value = ''
  if (weatherColorNeedsMetric(form.value, props.object)) {
    saveError.value = _t('Pick a metric — weather coloring needs one to colorize the line.')
    return
  }
  saving.value = true
  emit('save', updatesFromForm(form.value, props.object, props.mapType))
}

function onConfirmDelete(): void {
  confirmDelete.value = false
  emit('delete')
}
</script>

<template>
  <div
    ref="frame"
    class="maps-object-properties-modal"
    role="dialog"
    :aria-label="_t('Object properties')"
  >
    <!-- Takes the clicks beside the card; an edited card asks before they
         discard it. Keyboard users have Escape and the close
         button, so this is hidden from the a11y tree. -->
    <div class="maps-object-properties-modal__backdrop" aria-hidden="true" @click="requestClose" />
    <div
      class="maps-object-properties-modal__card"
      :class="`maps-object-properties-modal__card--${side}`"
      :style="cardStyle"
    >
      <!-- The header doubles as the drag handle that moves the card aside. -->
      <div
        class="maps-object-properties-modal__header"
        :class="{ 'maps-object-properties-modal__header--dragging': dragging }"
        @pointerdown="onHeaderPointerDown"
        @pointermove="onHeaderPointerMove"
        @pointerup="onHeaderPointerUp"
        @pointercancel="onHeaderPointerUp"
      >
        <CmkBadge type="outline" size="small">{{ objectTypeLabel(object.type, _t) }}</CmkBadge>
        <span class="maps-object-properties-modal__name">{{ displayName }}</span>
        <CmkIconButton
          name="close"
          size="xsmall"
          :title="_t('Close')"
          :aria-label="_t('Close')"
          @click="requestClose"
        />
      </div>

      <CmkScrollContainer class="maps-object-properties-modal__body">
        <IdentitySection
          v-if="showsIdentity"
          v-model:form="form"
          :object="object"
          :suggestions="suggestions"
        />
        <TextboxSection v-if="objectType === 'textbox'" v-model:form="form" />
        <template v-if="objectType === 'graph'">
          <GraphSourceSection
            v-model:form="form"
            :metrics="metrics"
            :source="graphSource"
            @update:source="setGraphSource"
          />
          <GraphEmbedSection v-model:form="form" />
        </template>
        <LineSection
          v-if="isLine"
          v-model:form="form"
          :object="object"
          :metrics="metrics"
          :map-type="mapType"
          @detach="emit('detach')"
        />
        <template v-if="!isLine">
          <PositionSection v-model:form="form" :map-type="mapType" />
          <LabelSection v-model:form="form" :object="object" />
        </template>
        <AppearanceSection
          v-if="showsAppearance"
          v-model:form="form"
          :metrics="metrics"
          :map-icon-size="mapIconSize"
        />
        <LinkSection v-model:form="form" :auto-url="autoUrl" />
        <FilterSection v-if="showsFilter" v-model:form="form" :is-host="boundType === 'host'" />
        <TemplatesSection v-model:form="form" :stateful="stateful" />
      </CmkScrollContainer>

      <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />

      <div class="maps-object-properties-modal__footer">
        <!-- Quiet like the delete actions elsewhere in Checkmk; the
             confirmation is where it turns red. -->
        <CmkButton @click="confirmDelete = true">
          <CmkIcon name="delete" variant="inline" size="small" />
          {{ _t('Delete') }}
        </CmkButton>
        <MapsConfirmDialog
          :open="confirmDelete"
          variant="error"
          :title="objectDeleteTitle(object, _t)"
          :message="_t('This cannot be undone.')"
          :confirm-label="_t('Delete')"
          @confirm="onConfirmDelete"
          @cancel="confirmDelete = false"
        />
        <MapsUnsavedChangesDialog
          :open="confirmDiscard"
          @confirm="discard"
          @cancel="confirmDiscard = false"
        />
        <div class="maps-object-properties-modal__actions">
          <CmkButton variant="secondary" @click="requestClose">{{ _t('Cancel') }}</CmkButton>
          <CmkButton variant="primary" :disabled="saving" @click="save">
            {{ saving ? _t('Saving…') : _t('Save') }}
          </CmkButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Embedded in the Checkmk page this is contained by the content area, not the
   viewport (``.maps-app--embed``), so the card sizes against ``%`` of this box
   — ``vw``/``vh`` would reach out under Checkmk's own chrome. */
.maps-object-properties-modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-index-modal);
}

.maps-object-properties-modal__backdrop {
  position: absolute;
  inset: 0;
}

/* At the top, centered until it knows where the object is; the transform
   carries the centering and the offset the header was dragged by. */
.maps-object-properties-modal__card {
  position: absolute;
  top: var(--dimension-8);
  left: 50%;
  display: flex;
  flex-direction: column;
  width: 504px;
  max-width: calc(100% - var(--dimension-8));
  max-height: calc(100% - 2 * var(--dimension-8));
  overflow: hidden;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--maps-shadow-canvas-overlay-high);
}

.maps-object-properties-modal__card--left {
  left: var(--dimension-8);
}

.maps-object-properties-modal__card--right {
  right: var(--dimension-8);
  left: auto;
}

.maps-object-properties-modal__header {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
  cursor: grab;
  border-bottom: 1px solid var(--default-border-color);
}

.maps-object-properties-modal__header--dragging {
  cursor: grabbing;
}

.maps-object-properties-modal__name {
  flex: 1;
  overflow: hidden;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-object-properties-modal__body {
  flex: 1;
  min-height: 0;
  padding: var(--dimension-5);
}

.maps-object-properties-modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
  border-top: 1px solid var(--default-border-color);
}

.maps-object-properties-modal__actions {
  display: flex;
  gap: var(--dimension-3);
}
</style>
