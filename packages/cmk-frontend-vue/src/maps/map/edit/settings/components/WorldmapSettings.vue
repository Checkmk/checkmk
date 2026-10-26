<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Where a geo map opens, which tiles it draws, and whether it populates itself
from the hosts' own coordinates.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onMounted, useTemplateRef, watch } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import {
  GEO_MAX_ZOOM,
  type SettingsFocus,
  type SettingsForm,
  geoViewOutOfRange
} from '@/maps/map/edit/settings/settingsForm'
import { useSettings } from '@/maps/services/context'
import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'
import { isAllowedTileUrl } from '@/maps/shared/worldmap/tileLayer'

const props = defineProps<{
  /** True once the operator tried to save, so gaps may be pointed out. */
  saveAttempted: boolean
  /** The option to bring into view and focus on opening. */
  initialFocus?: SettingsFocus | null
}>()

const form = defineModel<SettingsForm>('form', { required: true })

const emit = defineEmits<{ 'pick-view': [] }>()

const { _t } = usei18n()

const automapSource = useTemplateRef<HTMLElement>('automapSource')
const automapSourceDropdown =
  useTemplateRef<InstanceType<typeof CmkDropdown>>('automapSourceDropdown')
onMounted(() => {
  if (props.initialFocus === 'automap_source') {
    automapSource.value?.scrollIntoView({ block: 'center' })
    automapSourceDropdown.value?.focus()
  }
})

const autoSourceOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('None, place objects manually') },
    { name: 'all_hosts', title: _t('All hosts with geo coordinates') },
    { name: 'hostgroup', title: _t('Hosts in host group…') },
    { name: 'servicegroup', title: _t('Hosts hosting a service in service group…') }
  ]
}))

const groupKind = computed(() =>
  form.value.worldmap_auto_source === 'hostgroup' ||
  form.value.worldmap_auto_source === 'servicegroup'
    ? form.value.worldmap_auto_source
    : null
)

// A group picked for the other kind of group must not survive the swap; a
// detour over a choice without a group keeps it.
let pickedFor = groupKind.value
watch(groupKind, (kind) => {
  if (kind === null) {
    return
  }
  if (pickedFor !== null && kind !== pickedFor) {
    form.value.worldmap_auto_filter_value = ''
  }
  pickedFor = kind
})
const groupNameMissing = computed(
  () => props.saveAttempted && !form.value.worldmap_auto_filter_value
)

const outOfRange = computed(() => new Set(geoViewOutOfRange(form.value)))

// Tiles are fetched by the browser, so a server the site has not configured is
// blocked by the page policy and the map just stays empty — say it here.
const tiles = useSettings().tiles
const tileUrlBlocked = computed(
  () =>
    !!form.value.worldmap_tile_url &&
    !isAllowedTileUrl(form.value.worldmap_tile_url, tiles.value?.allowed_sources ?? [])
)
</script>

<template>
  <SettingsSection :title="_t('Map view')">
    <div class="maps-worldmap-settings__view">
      <div class="maps-worldmap-settings__coords">
        <EditField v-slot="{ id }" labels-control :label="_t('Latitude')">
          <CmkInput
            :id="id"
            v-model="form.worldmap_lat"
            type="number"
            min="-90"
            max="90"
            :external-errors="outOfRange.has('lat') ? [_t('Between -90 and 90.')] : []"
          />
        </EditField>
        <EditField v-slot="{ id }" labels-control :label="_t('Longitude')">
          <CmkInput
            :id="id"
            v-model="form.worldmap_lng"
            type="number"
            min="-180"
            max="180"
            :external-errors="outOfRange.has('lng') ? [_t('Between -180 and 180.')] : []"
          />
        </EditField>
        <EditField
          v-slot="{ id }"
          labels-control
          :label="_t('Zoom')"
          :help="_t('Pan/zoom the map first, then reopen settings to capture the current view.')"
        >
          <CmkInput
            :id="id"
            v-model="form.worldmap_zoom"
            type="number"
            min="0"
            :max="GEO_MAX_ZOOM"
            :external-errors="
              outOfRange.has('zoom')
                ? [_t('A whole number from 0 to %{max}.', { max: GEO_MAX_ZOOM })]
                : []
            "
          />
        </EditField>
      </div>
      <CmkButton
        variant="secondary"
        :title="_t('Closes settings and switches the map to picker mode.')"
        @click="emit('pick-view')"
      >
        <CmkIcon name="search" variant="inline" size="small" />
        <span>{{ _t('Pick from map') }}</span>
      </CmkButton>
    </div>

    <EditField
      v-slot="{ id }"
      labels-control
      :label="_t('Tile server URL')"
      :help="
        _t(
          'Leave empty for the site default. Only OpenStreetMap and the tile server configured in the global settings can be reached — tiles from anywhere else are blocked by the browser.'
        )
      "
    >
      <CmkInput
        :id="id"
        v-model="form.worldmap_tile_url"
        :placeholder="untranslated('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')"
        field-size="fill"
        :external-errors="
          tileUrlBlocked
            ? [_t('This server is not allowed by the site, its tiles would not load.')]
            : []
        "
      />
    </EditField>
    <EditField
      v-slot="{ id }"
      labels-control
      :label="_t('Map saturation (%)')"
      :help="_t('Left empty, the map shows at 100 %, in its full colors.')"
    >
      <CmkInput
        :id="id"
        v-model="form.worldmap_tile_saturate"
        type="number"
        :min="0"
        :max="100"
        :step="5"
        placeholder="100"
      />
    </EditField>

    <div ref="automapSource">
      <EditField
        :label="_t('Automatic object placement')"
        :help="
          _t(
            'Hosts are auto-discovered from monitoring data via maps_lat/maps_lng labels or LAT/LONG custom variables. They show up alongside any objects you place manually.'
          )
        "
      >
        <CmkDropdown
          ref="automapSourceDropdown"
          :model-value="form.worldmap_auto_source"
          :options="autoSourceOptions"
          :label="_t('Automatic object placement')"
          width="fill"
          @update:model-value="
            form.worldmap_auto_source = ($event ?? '') as typeof form.worldmap_auto_source
          "
        />
      </EditField>
    </div>
    <EditField v-if="groupKind" :label="_t('Group name')" required>
      <CmkInlineValidation
        :validation="groupNameMissing ? [_t('Pick a group to discover hosts from.')] : []"
      />
      <MapsObjectField
        v-model="form.worldmap_auto_filter_value"
        :kind="groupKind"
        :label="_t('Group name')"
        :placeholder="_t('Select a group')"
        :has-error="groupNameMissing"
      />
    </EditField>
  </SettingsSection>
</template>

<style scoped>
.maps-worldmap-settings__view {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-4);
}

.maps-worldmap-settings__coords {
  display: grid;
  flex: 1;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--dimension-4);
}
</style>
