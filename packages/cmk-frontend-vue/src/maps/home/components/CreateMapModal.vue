<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, onMounted, ref } from 'vue'

import { useConnections, useMaps, useSettings } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import { mapTypeOptions } from '@/maps/utils/dropdownOptions'
import { sanitizeMapName, sanitizeStrippedChars, slugToTitleCase } from '@/maps/utils/naming'

const emit = defineEmits<{ close: []; created: [name: string] }>()

const { _t } = usei18n()
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
    static: _t('Free placement of objects on a canvas or background image'),
    worldmap: _t('Objects positioned on an interactive world map using geo-coordinates'),
    flow: _t('Dynamic tree of all hosts and their relationships'),
    radar: _t('Automatic display of all hosts/services matching a group filter'),
    foldertree: _t(
      'Live status tree along the Checkmk SETUP folder hierarchy, with worst-state roll-up'
    ),
    presentation: _t('Design-first slide for dashboards and status walls — direct manipulation')
  }
  return mapTypeOptions(_t).map((o) => ({ ...o, desc: descriptions[o.name] ?? '' }))
})

const _NAME_RE = /^[a-zA-Z0-9_-]+$/
const _MAX_NAME_LEN = 64
const nameError = ref('')
const nameWarning = ref('')

function onNameInput(raw: string) {
  nameTouched.value = true
  const stripped = sanitizeStrippedChars(raw)
  form.value.name = sanitizeMapName(raw)
  if (form.value.name.length > _MAX_NAME_LEN) {
    nameError.value = _t('Map ID is too long (max %{max} characters)', { max: _MAX_NAME_LEN })
  } else if (form.value.name && !_NAME_RE.test(form.value.name)) {
    nameError.value = _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
  } else {
    nameError.value = ''
  }
  nameWarning.value = stripped
    ? _t('Some characters were removed (umlauts, punctuation, symbols are not allowed)')
    : ''
  if (!aliasTouched.value) {
    form.value.alias = slugToTitleCase(form.value.name)
  }
}

function onAliasInput() {
  aliasTouched.value = true
  if (!nameTouched.value) {
    form.value.name = sanitizeMapName(form.value.alias).toLowerCase()
    nameError.value =
      form.value.name && !_NAME_RE.test(form.value.name)
        ? _t('Only letters, digits, hyphens (-) and underscores (_) allowed')
        : ''
  }
}

function pickBackendId() {
  const ids = connectionsStore.connections.value.map((b) => b.id)
  const preferred = settingsStore.settings.value.default_backend_id
  return (preferred && ids.includes(preferred) ? preferred : ids[0]) ?? ''
}

const nameInput = ref<{ focus: () => void } | null>(null)

onMounted(async () => {
  // The dialog opens on the first field, so a map can be named right away.
  // CmkPopup renders through a portal, where the native autofocus attribute
  // does not fire; it also focuses its own container, so this has to come
  // after that.
  await nextTick()
  nameInput.value?.focus()
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
        <label for="maps-create-map-name" class="maps-create-map-modal__label">{{
          _t('Map ID')
        }}</label>
        <CmkInput
          id="maps-create-map-name"
          ref="nameInput"
          :model-value="form.name"
          placeholder="my-map"
          field-size="fill"
          @update:model-value="(v) => onNameInput(String(v ?? ''))"
        />
        <p v-if="nameError" class="maps-create-map-modal__error">{{ nameError }}</p>
        <p v-else-if="nameWarning" class="maps-create-map-modal__warning">{{ nameWarning }}</p>
        <p v-else class="maps-create-map-modal__hint">
          {{
            _t(
              'Letters, digits, hyphens and underscores only — spaces become hyphens automatically'
            )
          }}
        </p>
      </div>
      <div class="maps-create-map-modal__field">
        <label for="maps-create-map-alias" class="maps-create-map-modal__label">{{
          _t('Display name')
        }}</label>
        <CmkInput
          id="maps-create-map-alias"
          v-model="form.alias"
          :placeholder="_t('My map')"
          field-size="fill"
          @update:model-value="onAliasInput"
        />
      </div>
      <div class="maps-create-map-modal__field">
        <!-- Not a <label>: CmkDropdown is not labelable, it carries its own aria-label. -->
        <span class="maps-create-map-modal__label">{{ _t('Connection') }}</span>
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
          <CmkAlertBox variant="warning" size="small">
            {{ _t('No connections configured yet — create one first.') }}
            <!-- Connections live in Checkmk global settings; link out to WATO
                 (maps.py and wato.py share the /<site>/check_mk/ directory). -->
            <a
              href="wato.py?mode=edit_configvar&varname=maps_connections"
              class="maps-create-map-modal__link"
            >
              {{ _t('Manage connections →') }}
            </a>
          </CmkAlertBox>
        </template>
      </div>
      <div class="maps-create-map-modal__field">
        <!-- Not a <label>: the radiogroup below carries its own aria-label. -->
        <span class="maps-create-map-modal__label">{{ _t('Map type') }}</span>
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

.maps-create-map-modal__label {
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
}

.maps-create-map-modal__error {
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}

.maps-create-map-modal__warning {
  font-size: var(--font-size-normal);
  color: var(--color-yellow-50);
}

.maps-create-map-modal__hint {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-create-map-modal__link {
  display: block;
  margin-top: var(--dimension-3);
  color: var(--color-yellow-50);
  font-weight: var(--font-weight-bold);
  text-decoration: underline;
}

.maps-create-map-modal__type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--dimension-3);
}

.maps-create-map-modal__type-card {
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
  border-color: var(--color-corporate-green-50);
}

.maps-create-map-modal__type-card--selected {
  border-color: var(--color-corporate-green-50);
  background: color-mix(
    in srgb,
    var(--color-corporate-green-50) 10%,
    var(--default-form-element-bg-color)
  );
}

/* With an odd number of map types (currently 5) the last card would sit alone
   in a half-row; let it span the full width so the grid reads balanced. */
.maps-create-map-modal__type-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

.maps-create-map-modal__type-card-title {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-create-map-modal__type-card-desc {
  font-size: 11px;
  color: var(--font-color-dimmed);
  line-height: 1.35;
}
</style>
