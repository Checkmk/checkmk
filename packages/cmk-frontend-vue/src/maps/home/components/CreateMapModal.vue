<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, nextTick, onMounted, ref } from 'vue'

import { useConnections, useMaps, useSettings } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import { mapTypeOptions } from '@/maps/utils/dropdownOptions'
import {
  mapIdFromName,
  sanitizeMapName,
  sanitizeStrippedChars,
  slugToTitleCase
} from '@/maps/utils/naming'

const emit = defineEmits<{ close: []; created: [name: string] }>()

const { _t } = usei18n()
const aliasId = useId()
const nameId = useId()
const mapsStore = useMaps()
const connectionsStore = useConnections()
const settingsStore = useSettings()

const form = ref({ name: '', alias: '', connection_id: '', view_type: 'static' })
const aliasTouched = ref(false)
const nameTouched = ref(false)

const connectionOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: connectionsStore.connections.value.map((b) => ({
    name: b.id,
    title: untranslated(b.label || b.id)
  }))
}))
const mapTypeCards = computed(() => {
  const descriptions: Record<string, string> = {
    static: _t('Place objects on a blank canvas or a picture, such as a floor plan'),
    worldmap: _t('Show hosts, services and groups at their locations on a world map'),
    flow: _t('Lay out all hosts automatically by how they are connected'),
    radar: _t('Show all hosts or services, or those of one group, worst first'),
    foldertree: _t('Watch your Setup folders as a tree, each folder in its worst state'),
    presentation: _t('Design a slide for a status wall from text, shapes and live states')
  }
  return mapTypeOptions(_t).map((o) => ({ ...o, desc: descriptions[o.name] ?? '' }))
})

const nameError = ref('')
const nameWarning = ref('')
// A name in a script without Latin letters leaves nothing to fill an ID in from.
const nothingToDerive = computed(
  () => !nameTouched.value && !form.value.name && form.value.alias.trim() !== ''
)

function nameLengthError(name: string): string {
  const maxLength = settingsStore.mapNameMaxLength.value
  return maxLength !== null && name.length > maxLength
    ? _t('Map ID is too long (max %{max} characters)', { max: maxLength })
    : ''
}

// Until the site's limit is known, the backend is left to reject an ID that is too long.
function mapIdFromAlias(): string {
  return mapIdFromName(form.value.alias, settingsStore.mapNameMaxLength.value ?? Infinity)
}

function onNameInput(raw: string) {
  // An emptied ID goes back to following the display name.
  nameTouched.value = raw !== ''
  form.value.name = nameTouched.value ? sanitizeMapName(raw) : mapIdFromAlias()
  nameError.value = nameLengthError(form.value.name)
  nameWarning.value = sanitizeStrippedChars(raw)
    ? _t('Some characters were removed (umlauts, punctuation, symbols are not allowed)')
    : ''
  if (!aliasTouched.value) {
    form.value.alias = slugToTitleCase(form.value.name)
  }
}

function onAliasInput() {
  aliasTouched.value = true
  if (!nameTouched.value) {
    form.value.name = mapIdFromAlias()
    nameError.value = nameLengthError(form.value.name)
  }
}

function pickBackendId() {
  const ids = connectionsStore.connections.value.map((b) => b.id)
  const preferred = settingsStore.settings.value.default_backend_id
  return (preferred && ids.includes(preferred) ? preferred : ids[0]) ?? ''
}

const aliasInput = ref<{ focus: () => void } | null>(null)

onMounted(async () => {
  // The dialog opens on the display name, so a map can be named right away.
  // CmkPopup renders through a portal, where the native autofocus attribute
  // does not fire; it also focuses its own container, so this has to come
  // after that.
  await nextTick()
  aliasInput.value?.focus()
  await connectionsStore.fetch()
  form.value.connection_id = pickBackendId()
  form.value.view_type = settingsStore.settings.value.default_map_type || 'static'
})

async function submit() {
  nameError.value = ''
  try {
    await mapsStore.createMap(
      form.value.name,
      form.value.alias,
      form.value.connection_id,
      form.value.view_type,
      null,
      settingsStore.settings.value.default_render_mode
    )
  } catch (err) {
    if (err instanceof CmkApiError) {
      if (err.statusCode === 409) {
        nameError.value = _t('A map with this ID already exists')
      } else if (err.statusCode === 422) {
        nameError.value =
          err.message || _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
      } else {
        nameError.value = err.message || `HTTP ${err.statusCode}`
      }
    } else {
      // Never fail silently: surface any other error so the dialog does not just
      // sit there with the Create button doing nothing.
      nameError.value = err instanceof Error ? err.message : _t('Failed to create map')
    }
    return
  }
  const created = form.value.name
  form.value = {
    name: '',
    alias: '',
    connection_id: pickBackendId(),
    view_type: settingsStore.settings.value.default_map_type || 'static'
  }
  emit('created', created)
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Add map')" closable @close="$emit('close')">
    <form class="maps-create-map-modal__form" @submit.prevent="submit">
      <div class="maps-create-map-modal__field">
        <CmkLabel :for="aliasId">{{ _t('Display name') }}</CmkLabel>
        <CmkInput
          :id="aliasId"
          ref="aliasInput"
          v-model="form.alias"
          :placeholder="_t('My map')"
          field-size="fill"
          @update:model-value="onAliasInput"
        />
      </div>
      <div class="maps-create-map-modal__field">
        <CmkLabel :for="nameId">{{ _t('Map ID') }}</CmkLabel>
        <CmkInput
          :id="nameId"
          :model-value="form.name"
          placeholder="my-map"
          field-size="fill"
          @update:model-value="(v) => onNameInput(String(v ?? ''))"
        />
        <p v-if="nameError" class="maps-create-map-modal__error">{{ nameError }}</p>
        <p v-else-if="nameWarning" class="maps-create-map-modal__warning">{{ nameWarning }}</p>
        <p v-else-if="nothingToDerive" class="maps-create-map-modal__warning">
          {{ _t('This name has no letters or digits to fill in an ID from. Enter a map ID.') }}
        </p>
        <p v-else class="maps-create-map-modal__hint">
          {{
            _t(
              'The ID is used in the URL of the map and is filled in from the display name. Use only letters, digits, hyphens (-) and underscores (_).'
            )
          }}
        </p>
      </div>
      <div class="maps-create-map-modal__field">
        <!-- Bound to nothing: CmkDropdown is not labelable, it carries its own aria-label. -->
        <CmkLabel>{{ _t('Connection') }}</CmkLabel>
        <template v-if="connectionsStore.connections.value.length > 0">
          <CmkDropdown
            :model-value="form.connection_id || null"
            :options="connectionOptions"
            :width="'fill'"
            :label="_t('Connection')"
            @update:model-value="form.connection_id = $event ?? ''"
          />
        </template>
        <template v-else>
          <CmkAlertBoxDeprecated variant="warning" size="small">
            {{ _t('No connections configured yet — create one first.') }}
            <!-- Connections live in Checkmk global settings; link out to WATO
                 (maps.py and wato.py share the /<site>/check_mk/ directory). -->
            <a
              href="wato.py?mode=edit_configvar&varname=maps_connections"
              class="maps-create-map-modal__link"
            >
              {{ _t('Manage connections →') }}
            </a>
          </CmkAlertBoxDeprecated>
        </template>
      </div>
      <div class="maps-create-map-modal__field">
        <!-- Bound to nothing: the radiogroup below carries its own aria-label. -->
        <CmkLabel>{{ _t('Map type') }}</CmkLabel>
        <div
          class="maps-create-map-modal__type-grid"
          role="radiogroup"
          :aria-label="_t('Map type')"
        >
          <button
            v-for="opt in mapTypeCards"
            :key="opt.name"
            type="button"
            role="radio"
            :aria-checked="form.view_type === opt.name"
            class="maps-create-map-modal__type-card"
            :class="{
              'maps-create-map-modal__type-card--selected': form.view_type === opt.name
            }"
            @click="form.view_type = opt.name"
          >
            <span class="maps-create-map-modal__type-card-title">{{ opt.title }}</span>
            <span class="maps-create-map-modal__type-card-desc">{{ opt.desc }}</span>
          </button>
        </div>
      </div>
    </form>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        variant="primary"
        :disabled="!form.name || !!nameError || !form.connection_id"
        @click="submit"
      >
        {{ _t('Create') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-create-map-modal__form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  min-width: 380px;
}

.maps-create-map-modal__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-create-map-modal__error {
  font-size: var(--font-size-normal);
  color: var(--status-text-color-error-pale);
}

.maps-create-map-modal__warning {
  font-size: var(--font-size-normal);
  color: var(--status-text-color-warning);
}

.maps-create-map-modal__hint {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-create-map-modal__link {
  display: block;
  margin-top: var(--dimension-3);
  color: var(--status-text-color-warning);
  font-weight: var(--font-weight-bold);
  text-decoration: underline;
}

.maps-create-map-modal__type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-3);
}

/* The theme gives every button a side margin and bold text. */
.maps-create-map-modal__type-card {
  margin: 0;
  font-weight: var(--font-weight-default);
  text-align: left;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  transition:
    border-color 120ms,
    background-color 120ms;
}

.maps-create-map-modal__type-card:hover {
  border-color: var(--interactive-accent);
}

.maps-create-map-modal__type-card--selected {
  border-color: var(--interactive-accent);
  background: color-mix(
    in srgb,
    var(--interactive-accent) 10%,
    var(--default-form-element-bg-color)
  );
}

/* With an odd number of map types the last card would sit alone in a half-row;
   let it span the full width so the grid reads balanced. */
.maps-create-map-modal__type-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.maps-create-map-modal__type-card-title {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-create-map-modal__type-card-desc {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  line-height: 1.35;
}
</style>
