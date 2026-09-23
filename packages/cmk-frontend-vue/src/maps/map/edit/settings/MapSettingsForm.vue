<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Everything about a map that is not its content: what it is called, what it
reads from, how it is drawn, who may see it — beside a live preview of the map
as the form currently describes it.

The generic part is Checkmk's own metadata FormSpec, so it looks and validates
like every other Checkmk form. The per-type view fields sit below it as
hand-written blocks, because they are the map's own vocabulary rather than
anything the FormSpec layer knows about.
-->
<script setup lang="ts">
import type {
  ValidationMessage,
  VueFormspecComponents
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import FormEdit from '@/form/FormEdit.vue'
import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

import type { FormSchemaName } from '@/maps/api/formSchemas'
import FolderTreeSettings from '@/maps/map/edit/settings/components/FolderTreeSettings.vue'
import MapAccessTab from '@/maps/map/edit/settings/components/MapAccessTab.vue'
import MapSettingsPreview from '@/maps/map/edit/settings/components/MapSettingsPreview.vue'
import ProblemsOnlySettings from '@/maps/map/edit/settings/components/ProblemsOnlySettings.vue'
import RadarSettings from '@/maps/map/edit/settings/components/RadarSettings.vue'
import StaticMapSettings from '@/maps/map/edit/settings/components/StaticMapSettings.vue'
import WorldmapSettings from '@/maps/map/edit/settings/components/WorldmapSettings.vue'
import {
  flowViewData,
  formFromMap,
  hiddenMetadataFields,
  metadataFormData,
  metadataOverridesFrom,
  previewPatch,
  viewFromForm
} from '@/maps/map/edit/settings/settingsForm'
import { useMapAccess } from '@/maps/map/edit/settings/useMapAccess'
import { useSettingsPreview } from '@/maps/map/edit/settings/useSettingsPreview'
import { useStagedBackgroundImage } from '@/maps/map/edit/settings/useStagedBackgroundImage'
import { useMaps, useMapsApis, useToast } from '@/maps/services/context'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import MapsUnsavedChangesDialog from '@/maps/shared/components/MapsUnsavedChangesDialog.vue'
import type { MapRead, MapView } from '@/maps/types/api'
import { asFormSpecSchema } from '@/maps/utils/formSpec'
import { describeFieldProblems, toFormValidation } from '@/maps/utils/formValidation'
import { newMapElement, newObjectState } from '@/maps/utils/model'
import { interpolateTemplate } from '@/maps/utils/template'

const props = defineProps<{
  map: MapRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
  parentMapSize?: { width: number; height: number } | null
}>()

const emit = defineEmits<{
  close: []
  updated: []
  pickWorldmapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void]
  worldmapViewChange: [view: { lat: number; lng: number; zoom: number }]
}>()

const { _t } = usei18n()
const { mapConfig, formSchemas } = useMapsApis()
const mapsStore = useMaps()
const toast = useToast()

type Schema = NonNullable<VueFormspecComponents['components']>

const form = ref(formFromMap(props.map, props.worldmapView))
const formSpecData = ref<Record<string, unknown>>(metadataFormData(props.map))
const flowViewFormSpecData = ref<Record<string, unknown>>(flowViewData(props.map))

const formSchema = ref<Schema | null>(null)
const flowViewFormSchema = ref<Schema | null>(null)
const schemaLoading = ref(true)
const formBackendValidation = ref<ValidationMessage[]>([])

initializeComponentRegistry()

// Settings and Access, the way the other visuals separate their content form
// from their visibility: a map is a Checkmk visual, so who may see it is the
// visual's ``public`` field rather than a permission grid of its own.
const activeTab = ref('general')

const access = useMapAccess(() => props.map)
const background = useStagedBackgroundImage()

const saving = ref(false)
const saveError = ref('')
const saveAttempted = ref(false)

const mapType = computed(() => form.value.map_type)

// A group-scoped source needs the group it is scoped to; nothing else on these
// hand-written blocks can be left half-filled.
const missingFields = computed<string[]>(() => {
  const missing: string[] = []
  const needsGroup = (value: string) => value === 'hostgroup' || value === 'servicegroup'
  if (
    mapType.value === 'radar' &&
    needsGroup(form.value.radar_filter) &&
    !form.value.radar_filter_value
  ) {
    missing.push(_t('Group name'))
  }
  if (
    mapType.value === 'worldmap' &&
    needsGroup(form.value.worldmap_auto_source) &&
    !form.value.worldmap_auto_filter_value
  ) {
    missing.push(_t('Group name'))
  }
  return missing
})
const isComplete = computed(() => missingFields.value.length === 0)

const errorMessages = computed<string[]>(() => {
  const messages = saveAttempted.value
    ? missingFields.value.map((field) => _t('%{field} is required.', { field }))
    : []
  return saveError.value ? [...messages, saveError.value] : messages
})

// ---- Live preview ----

const PREVIEW_PREF_KEY = 'maps.mapSettings.previewVisible'
const showPreview = ref(window.localStorage?.getItem(PREVIEW_PREF_KEY) === '1')

function togglePreview(): void {
  showPreview.value = !showPreview.value
  try {
    window.localStorage?.setItem(PREVIEW_PREF_KEY, showPreview.value ? '1' : '0')
  } catch {
    // Private mode, or storage full — the toggle then only holds for this
    // session, which is better than failing the click.
  }
}

// True once the operator moved the view themselves, which stops the preview
// from matching the parent map's zoom.
const viewEdited = ref(false)

const preview = useSettingsPreview({
  mapName: () => props.map.name,
  patch: () =>
    previewPatch(form.value, formSpecData.value, flowViewFormSpecData.value, props.map.alias),
  backgroundImage: () =>
    background.removed.value
      ? null
      : (background.previewUrl.value ?? form.value.background_image) || null,
  parentMapSize: () => props.parentMapSize,
  viewEdited: () => viewEdited.value,
  isGeoMap: () => mapType.value === 'worldmap'
})

watch([form, formSpecData, flowViewFormSpecData], preview.schedule, { deep: true })
watch([background.previewUrl, background.removed], preview.postBackground)

watch(
  () => [form.value.worldmap_lat, form.value.worldmap_lng, form.value.worldmap_zoom] as const,
  ([lat, lng, zoom]) => {
    viewEdited.value = true
    if (mapType.value === 'worldmap') {
      emit('worldmapViewChange', { lat, lng, zoom })
    }
  }
)

// The parent map can push a view in while the form is already open (its
// "save current view as default" action), long after the form read the map.
watch(
  () => props.worldmapView,
  (next) => {
    if (
      !next ||
      (form.value.worldmap_lat === next.lat &&
        form.value.worldmap_lng === next.lng &&
        form.value.worldmap_zoom === next.zoom)
    ) {
      return
    }
    form.value.worldmap_lat = next.lat
    form.value.worldmap_lng = next.lng
    form.value.worldmap_zoom = next.zoom
  }
)

// ---- Picking the view on the map itself ----

const isPickingView = ref(false)

function startWorldmapViewPick(): void {
  if (isPickingView.value) {
    return
  }
  isPickingView.value = true
  emit('pickWorldmapView', (view) => {
    isPickingView.value = false
    if (!view) {
      return
    }
    form.value.worldmap_lat = view.lat
    form.value.worldmap_lng = view.lng
    form.value.worldmap_zoom = view.zoom
    // A picked view comes from the parent canvas, so the preview may go back
    // to compensating its own zoom once the watcher above has run.
    void nextTick(() => {
      viewEdited.value = false
    })
  })
}

// ---- Unsaved changes ----

/**
 * The form as it was, for both "has anything changed" and "put it back".
 *
 * The baseline holds the map's stored view rather than a geo view prefilled
 * from the parent canvas — otherwise opening the form on a panned map would
 * look like an edit nobody made.
 */
function baseline(): string {
  const stored = props.map.view.type === 'worldmap' ? props.map.view : null
  return JSON.stringify({
    form: stored
      ? {
          ...form.value,
          worldmap_lat: stored.lat,
          worldmap_lng: stored.lng,
          worldmap_zoom: stored.zoom
        }
      : { ...form.value },
    formSpec: formSpecData.value,
    flowView: flowViewFormSpecData.value,
    access: access.snapshot()
  })
}

const initialSnapshot = ref(baseline())

const isDirty = computed(
  () =>
    JSON.stringify({
      form: form.value,
      formSpec: formSpecData.value,
      flowView: flowViewFormSpecData.value,
      access: access.snapshot()
    }) !== initialSnapshot.value || background.changed.value
)

const discardDialogOpen = ref(false)

function requestClose(): void {
  if (isDirty.value) {
    discardDialogOpen.value = true
    return
  }
  emit('close')
}

function onSlideInClose(): void {
  // While picking, the slide-in is only hidden — Escape and the backdrop must
  // not end the pick, nor ask about discarding.
  if (!isPickingView.value) {
    requestClose()
  }
}

function resetChanges(): void {
  const snapshot = JSON.parse(initialSnapshot.value) as {
    form: typeof form.value
    formSpec: Record<string, unknown>
    flowView: Record<string, unknown>
    access: string
  }
  form.value = snapshot.form
  formSpecData.value = snapshot.formSpec
  flowViewFormSpecData.value = snapshot.flowView
  const restored = JSON.parse(snapshot.access) as {
    mode: typeof access.mode.value
    groups: string[]
    sites: string[]
    hideInMonitorMenu: boolean
  }
  access.mode.value = restored.mode
  access.groups.value = restored.groups
  access.sites.value = restored.sites
  access.hideInMonitorMenu.value = restored.hideInMonitorMenu
  background.reset()
  saveAttempted.value = false
  formBackendValidation.value = []
  saveError.value = ''
}

// ---- Saving ----

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '')
const saveShortcut = isMac ? '⌘S' : 'Ctrl+S'

const saveTooltip = computed(() => {
  if (saving.value) {
    return ''
  }
  if (!isDirty.value) {
    return _t('No changes to save')
  }
  if (saveAttempted.value && !isComplete.value) {
    return _t('Fix the highlighted fields to save')
  }
  return _t('Save (%{shortcut})', { shortcut: saveShortcut })
})

const canSave = computed(
  () => !saving.value && isDirty.value && !(saveAttempted.value && !isComplete.value)
)

function onKeydown(event: KeyboardEvent): void {
  if (!(isMac ? event.metaKey : event.ctrlKey)) {
    return
  }
  if (event.key === 's' || event.key === 'S' || event.key === 'Enter') {
    event.preventDefault()
    if (canSave.value && isComplete.value) {
      void save()
    }
  }
}

/**
 * The map's own view block, plus what only the running map knows.
 *
 * A flow map's node positions and service layout are written by the view
 * itself, so they are read back fresh and carried over — building the view
 * from the form alone would throw the operator's arrangement away.
 */
async function viewToSave(flowValues: Record<string, unknown>): Promise<Record<string, unknown>> {
  const view = viewFromForm(form.value, flowValues)
  if (form.value.map_type !== 'flow') {
    return view
  }
  const fresh = await mapsStore.getMap(props.map.name)
  const flow = fresh.view?.type === 'flow' ? fresh.view : null
  return { ...view, service_layout: flow?.service_layout ?? null, positions: flow?.positions ?? {} }
}

/**
 * A form's values as they are stored, or ``null`` when the form spec refused
 * them.
 *
 * The bag a form produced is not what gets stored — a single-choice field
 * carries an opaque id per element — so it goes back through the form spec on
 * the server. Its validators run there too, which is why a rejection lands on
 * the field that carries it instead of arriving later as an API error with no
 * field to blame.
 */
async function storedValues(
  spec: FormSchemaName,
  values: Record<string, unknown>
): Promise<Record<string, unknown> | null> {
  const result = await formSchemas.parse(spec, values)
  if (result.validation) {
    formBackendValidation.value = result.validation
    saveError.value = _t('Please correct the highlighted fields.')
    return null
  }
  return result.data
}

async function save(): Promise<void> {
  saveAttempted.value = true
  if (!isComplete.value) {
    return
  }
  saving.value = true
  saveError.value = ''
  formBackendValidation.value = []
  try {
    // Translated (and validated) before anything is written, so a value the
    // form spec refuses does not leave an uploaded background behind.
    const formSpec = await storedValues('map_metadata', formSpecData.value)
    if (!formSpec) {
      return
    }
    const flowValues =
      mapType.value === 'flow' ? await storedValues('flow_view', flowViewFormSpecData.value) : {}
    if (!flowValues) {
      return
    }

    // The staged background only reaches the server now, so closing the form
    // without saving never leaves a file behind. The daemon stores the file;
    // the field naming it is persisted by the metadata save below.
    if (background.removed.value) {
      await mapConfig.deleteBackground(props.map.name)
      form.value.background_image = ''
    } else if (background.file.value) {
      const { filename } = await mapConfig.uploadBackground(props.map.name, background.file.value)
      form.value.background_image = filename
    }

    const view = await viewToSave(flowValues)
    await mapsStore.saveMapMetadata(
      props.map.name,
      {
        ...metadataOverridesFrom(formSpec),
        background_image: form.value.background_image || null,
        background_color: form.value.background_color || null,
        // A presentation's slides — elements, theme, size, background — are
        // owned and autosaved by its canvas; sending a metadata-only view
        // here would blank them. The view is assembled as a loose record but
        // is a valid variant by construction.
        ...(mapType.value === 'presentation' ? {} : { view: view as unknown as MapView })
      },
      // Visibility and the Monitor menu live in the pagetype envelope rather
      // than the map itself, so they are sent explicitly.
      access.desired()
    )

    initialSnapshot.value = JSON.stringify({
      form: form.value,
      formSpec: formSpecData.value,
      flowView: flowViewFormSpecData.value,
      access: access.snapshot()
    })
    if (background.changed.value) {
      mapsStore.bumpBgRefreshTick(props.map.name)
    }
    background.reset()
    saveAttempted.value = false
    toast.success(_t('Map settings saved'), { label: _t('Open map'), onClick: openMap })
    emit('updated')
  } catch (error: unknown) {
    saveError.value = messageFor(error)
  } finally {
    saving.value = false
  }
}

/** What to tell the operator about a failed save. */
function messageFor(error: unknown): string {
  if (error instanceof CmkApiError && error.statusCode === 409) {
    return _t(
      'Map changed elsewhere — close and reopen to apply your edit on top of the latest version.'
    )
  }
  if (error instanceof CmkApiError && error.statusCode === 422) {
    const detail = (error.body as { detail?: unknown } | null)?.detail
    const parsed = toFormValidation(detail, new Set(Object.keys(formSpecData.value)))
    if (parsed) {
      formBackendValidation.value = parsed.messages
      return parsed.stray.map((message) => message.message).join(' ')
    }
    return error.message
  }
  if (error instanceof CmkApiError) {
    // A rejected field comes with the value that was rejected; say which, or
    // the operator is left with "these fields have problems" and no value.
    const problems = describeFieldProblems(error.body)
    if (problems) {
      return `${error.message} ${problems}`
    }
  }
  return error instanceof Error ? error.message : _t('An error occurred')
}

// ---- Deleting ----

const deleteDialogOpen = ref(false)

const deleteTitle = computed(() =>
  _t('Delete map "%{name}"?', { name: props.map.alias || props.map.name })
)

function confirmDiscard(): void {
  discardDialogOpen.value = false
  emit('close')
}

async function confirmDelete(): Promise<void> {
  deleteDialogOpen.value = false
  const label = props.map.alias || props.map.name
  try {
    await mapsStore.deleteMap(props.map.name)
    toast.success(_t('Map "%{name}" deleted', { name: label }))
    emit('updated')
    emit('close')
  } catch (error: unknown) {
    saveError.value = messageFor(error)
  }
}

// ---- Chrome ----

const mapTitle = computed(() => {
  const alias = form.value.alias || props.map.name
  const head = `${_t('Map settings')} — ${alias}`
  return alias === props.map.name ? head : `${head} · ${props.map.name}`
})

function openMap(): void {
  emit('close')
  // Navigation goes through real query parameters, not a hash route.
  window.location.href = `${window.location.pathname}?name=${encodeURIComponent(props.map.name)}`
}

/** The hover template as it would read on a real object. */
const templatePreview = computed(() => {
  const template = (formSpecData.value.hover_template as string | undefined)?.trim()
  if (!template) {
    return ''
  }
  const object = newMapElement({
    id: 'demo',
    type: 'service',
    host_name: 'db-prod-01',
    service_description: 'HTTP',
    z: 0,
    url_target: '_self'
  })
  const state = newObjectState({
    object_id: 'demo',
    type: 'service',
    state: 'CRITICAL',
    output: 'TCP connection refused'
  })
  try {
    return interpolateTemplate(template, object, state)
  } catch {
    return ''
  }
})

onMounted(async () => {
  // Registered before the awaits below: closing the slide-in while the schemas
  // are still in flight would otherwise run the removal first and leave the
  // listener attached for the life of the page.
  window.addEventListener('keydown', onKeydown)

  const flowSchema =
    mapType.value === 'flow'
      ? formSchemas.fetch('flow_view', flowViewData(props.map)).catch((): null => null)
      : Promise.resolve(null)
  const [metadataSpec, flowSpec] = await Promise.all([
    formSchemas.fetch('map_metadata', metadataFormData(props.map)).catch((): null => null),
    flowSchema
  ])
  schemaLoading.value = false

  // The values come back beside the schema because a form's values are not
  // the stored ones: a single-choice field carries an opaque id per element
  // that only the form spec can translate. Keeping the locally built bag when
  // the request fails leaves the form no worse off than not loading at all.
  //
  // Only the rendered fields are narrowed by map type. The values keep every
  // field, including the ones this type does not show, so that saving cannot
  // reset a value the operator never got to see.
  if (metadataSpec) {
    const hidden = hiddenMetadataFields(mapType.value)
    if (hidden.size > 0) {
      const dictionary = metadataSpec.schema as { elements?: { name: string }[] }
      if (Array.isArray(dictionary.elements)) {
        dictionary.elements = dictionary.elements.filter((element) => !hidden.has(element.name))
      }
    }
    formSchema.value = asFormSpecSchema(metadataSpec.schema)
    formSpecData.value = metadataSpec.data
  }
  if (flowSpec) {
    flowViewFormSchema.value = asFormSpecSchema(flowSpec.schema)
    flowViewFormSpecData.value = flowSpec.data
  }

  // FormEdit normalises the data bag on its first render (filling optional
  // fields with defaults); snapshotting before that would read as an edit.
  await nextTick()
  initialSnapshot.value = baseline()
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <CmkSlideInDialog
    :open="!isPickingView"
    :header="{ title: mapTitle, closeButton: true }"
    :size="showPreview ? 'medium' : 'small'"
    @close="onSlideInClose"
  >
    <div class="maps-map-settings-form">
      <div class="maps-map-settings-form__layout">
        <div class="maps-map-settings-form__body">
          <CmkTabs v-model="activeTab">
            <template #tabs>
              <CmkTab id="general">{{ _t('Settings') }}</CmkTab>
              <CmkTab id="access">{{ _t('Access') }}</CmkTab>
            </template>

            <template #tab-contents>
              <CmkTabContent id="general">
                <div class="maps-map-settings-form__fields">
                  <!-- The generic metadata comes first: a map is named and wired
                     up before its type-specific view is tuned. -->
                  <FormEdit
                    v-if="formSchema"
                    v-model:data="formSpecData"
                    :spec="formSchema"
                    :backend-validation="formBackendValidation"
                  />
                  <CmkLoading v-else-if="schemaLoading" />

                  <p v-if="templatePreview" class="maps-map-settings-form__template-preview">
                    <span>{{ _t('Hover preview:') }}</span>
                    <code>{{ templatePreview }}</code>
                  </p>

                  <StaticMapSettings
                    v-if="mapType === 'static'"
                    v-model:form="form"
                    :background="background"
                  />
                  <WorldmapSettings
                    v-else-if="mapType === 'worldmap'"
                    v-model:form="form"
                    :save-attempted="saveAttempted"
                    @pick-view="startWorldmapViewPick"
                  />
                  <!-- A flow map's view fields are a FormSpec too, so their
                     titles, help and inputs match the block above. -->
                  <FormEdit
                    v-else-if="mapType === 'flow' && flowViewFormSchema"
                    v-model:data="flowViewFormSpecData"
                    :spec="flowViewFormSchema"
                    :backend-validation="[]"
                  />
                  <RadarSettings
                    v-else-if="mapType === 'radar'"
                    v-model:form="form"
                    :save-attempted="saveAttempted"
                  />
                  <FolderTreeSettings v-else-if="mapType === 'foldertree'" v-model:form="form" />
                  <!-- A folder tree carries the filter in its own block, next to
                     the severity it narrows to. -->
                  <ProblemsOnlySettings
                    v-if="mapType !== 'foldertree' && mapType !== 'presentation'"
                    v-model:form="form"
                  />

                  <CmkAlertBox v-if="errorMessages.length" variant="error">
                    <div v-for="message in errorMessages" :key="message">{{ message }}</div>
                  </CmkAlertBox>
                </div>
              </CmkTabContent>

              <CmkTabContent id="access">
                <MapAccessTab :access="access" />
              </CmkTabContent>
            </template>
          </CmkTabs>
        </div>

        <!-- Dropped on a narrow viewport, where two columns do not fit. -->
        <MapSettingsPreview v-if="showPreview" :preview="preview" />
      </div>

      <div class="maps-map-settings-form__footer">
        <CmkButton v-if="isDirty" variant="optional" :disabled="saving" @click="resetChanges">
          {{ _t('Reset') }}
        </CmkButton>
        <CmkButton
          variant="optional"
          :icon="{ name: 'view', size: 'small' }"
          @click="togglePreview"
        >
          {{ showPreview ? _t('Hide preview') : _t('Show preview') }}
        </CmkButton>
        <span class="maps-map-settings-form__spacer" />
        <CmkButton v-if="map.can_delete" variant="danger" @click="deleteDialogOpen = true">
          {{ _t('Delete map…') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="requestClose">{{ _t('Close') }}</CmkButton>
        <CmkButton variant="primary" :disabled="!canSave" :title="saveTooltip" @click="save">
          {{ saving ? _t('Saving…') : _t('Save') }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>

  <MapsUnsavedChangesDialog
    :open="discardDialogOpen"
    @confirm="confirmDiscard"
    @cancel="discardDialogOpen = false"
  />
  <MapsConfirmDialog
    :open="deleteDialogOpen"
    variant="error"
    :title="deleteTitle"
    :message="
      _t(
        'This permanently removes the map configuration. Existing object data on other maps is unaffected.'
      )
    "
    :confirm-label="_t('Delete map…')"
    @confirm="confirmDelete"
    @cancel="deleteDialogOpen = false"
  />
</template>

<style scoped>
.maps-map-settings-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.maps-map-settings-form__layout {
  display: flex;
  gap: var(--dimension-6);
}

.maps-map-settings-form__body {
  flex: 1 1 60%;
  min-width: 0;
}

.maps-map-settings-form__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
}

.maps-map-settings-form__template-preview {
  display: flex;
  gap: var(--dimension-3);
  margin: 0;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-map-settings-form__footer {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding-top: var(--dimension-5);
  border-top: 1px solid var(--default-border-color);
}

.maps-map-settings-form__spacer {
  flex: 1;
}

@media (width <= 900px) {
  .maps-map-settings-form__layout {
    flex-direction: column;
  }
}
</style>
