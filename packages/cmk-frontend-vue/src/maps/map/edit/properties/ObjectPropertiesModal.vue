<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Everything about one object on a map, as a card beside the object itself.

The card is a popover when the operator reached it from the object (it stays
anchored to it, and can be dragged aside), and a centered dialog when there is
no anchor to sit next to. Which properties it shows follows from the object's
type — the sections decide that for themselves.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { useObjectMetrics } from '@/maps/map/edit/composables/useObjectMetrics'
import { useObjectSuggestions } from '@/maps/map/edit/composables/useObjectSuggestions'
import { usePropertiesPopover } from '@/maps/map/edit/composables/usePropertiesPopover'
import {
  type GraphSource,
  applyGraphSource,
  graphSourceOf
} from '@/maps/map/edit/properties/graphSource'
import {
  type ObjectForm,
  formFromObject,
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
import { useEscapeClose } from '@/maps/shared/composables/useEscapeClose'
import type { MapElement, MapViewType, ObjectState } from '@/maps/types/api'
import { objectDeleteTitle, objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { buildCheckmkViewUrl } from '@/maps/utils/mapNavigation'
import { getMapElementName } from '@/maps/utils/naming'

const props = defineProps<{
  object: MapElement
  state?: ObjectState | undefined
  connectionId: string
  mapType?: MapViewType | undefined
  mapIconSize?: number | null
  mapDefaultZ?: number
  checkmkUrl?: string | null
  anchorRect?: { left: number; top: number; right: number; bottom: number } | null
}>()

const emit = defineEmits<{
  close: []
  save: [updates: Record<string, unknown>]
  delete: []
  detach: []
}>()

const { _t } = usei18n()

useEscapeClose(() => emit('close'))

const form = ref<ObjectForm>(formFromObject(props.object, { z: props.mapDefaultZ ?? 1 }))
const graphSource = ref<GraphSource>(graphSourceOf(props.object))

// Another object may be selected while the card is open (the canvas keeps
// working underneath it), so the form follows whatever it is showing.
watch(
  () => props.object,
  (object) => {
    form.value = formFromObject(object, { z: props.mapDefaultZ ?? 1 })
    graphSource.value = graphSourceOf(object)
  }
)

function setGraphSource(source: GraphSource): void {
  graphSource.value = source
  applyGraphSource(form.value, source)
}

// The per-object connection override wins over the map's own.
const connectionId = computed(() => form.value.connection_id || props.connectionId)

const suggestions = useObjectSuggestions({
  connectionId: () => connectionId.value,
  objectType: () => props.object.type,
  hostName: () => form.value.host_name,
  mapName: () => form.value.map_name
})

const metrics = useObjectMetrics({
  object: () => props.object,
  state: () => props.state,
  connectionId: () => connectionId.value,
  hostName: () => form.value.host_name,
  serviceDescription: () => form.value.service_description
})

const card = ref<HTMLElement | null>(null)

const {
  isPopover,
  cardStyle,
  dragging,
  onHeaderPointerDown,
  onHeaderPointerMove,
  onHeaderPointerUp
} = usePropertiesPopover({
  anchorRect: () => props.anchorRect,
  object: () => props.object,
  card
})

const displayName = computed(() => getMapElementName(props.object) ?? '')

/** The object's own page in Checkmk, offered as the link field's default. */
const autoUrl = computed((): string | null => {
  const options = { site: props.state?.site_id ?? null }
  const { type } = props.object
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
const showsIdentity = computed(
  () => !['textbox', 'line', 'graph', 'image'].includes(objectType.value)
)
const showsAppearance = computed(() => !['line', 'textbox', 'graph'].includes(objectType.value))
// Every object that stands for more than itself can hide members -- including
// the BI aggregation, which is also the only one whose leaves the section can
// count back at the operator.
const showsFilter = computed(() =>
  ['host', 'hostgroup', 'servicegroup', 'map', 'aggregation'].includes(objectType.value)
)

const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)

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
    class="maps-object-properties-modal"
    :class="{ 'maps-object-properties-modal--centered': !isPopover }"
    role="dialog"
    :aria-label="_t('Object properties')"
  >
    <!-- Clicking beside the card closes it. Keyboard users have Escape and the
         close button, so this is hidden from the a11y tree. -->
    <div
      class="maps-object-properties-modal__backdrop"
      :class="{ 'maps-object-properties-modal__backdrop--dim': !isPopover }"
      aria-hidden="true"
      @click="emit('close')"
    />
    <div
      ref="card"
      class="maps-object-properties-modal__card"
      :class="
        isPopover
          ? 'maps-object-properties-modal__card--popover'
          : 'maps-object-properties-modal__card--modal'
      "
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
          @click="emit('close')"
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
            :suggestions="suggestions"
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
          :suggestions="suggestions"
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
        <FilterSection v-if="showsFilter" v-model:form="form" :connection-id="connectionId" />
        <TemplatesSection v-model:form="form" />
      </CmkScrollContainer>

      <CmkAlertBox v-if="saveError" variant="error">{{ saveError }}</CmkAlertBox>

      <div class="maps-object-properties-modal__footer">
        <CmkButton variant="danger" @click="confirmDelete = true">{{ _t('Delete') }}</CmkButton>
        <MapsConfirmDialog
          :open="confirmDelete"
          variant="error"
          :title="objectDeleteTitle(object, _t)"
          :message="_t('This cannot be undone.')"
          :confirm-label="_t('Delete')"
          @confirm="onConfirmDelete"
          @cancel="confirmDelete = false"
        />
        <div class="maps-object-properties-modal__actions">
          <CmkButton variant="secondary" @click="emit('close')">{{ _t('Cancel') }}</CmkButton>
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

.maps-object-properties-modal--centered {
  display: flex;
  align-items: center;
  justify-content: center;
}

.maps-object-properties-modal__backdrop {
  position: absolute;
  inset: 0;
}

.maps-object-properties-modal__backdrop--dim {
  background: rgb(0 0 0 / 60%);
  backdrop-filter: blur(4px);
}

.maps-object-properties-modal__card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-width: calc(100% - var(--dimension-8));
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);

  /* No elevation token exists in the design system, and this card has to lift
     off the map behind it — so the shadow stays a literal. */
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 60%);
}

.maps-object-properties-modal__card--popover {
  position: absolute;
  width: 400px;
  max-height: 75%;
}

.maps-object-properties-modal__card--modal {
  position: relative;
  width: 504px;
  max-height: 90%;
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
