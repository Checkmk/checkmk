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
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'
import { useSettings } from '@/maps/services/context'
import { isAllowedTileUrl } from '@/maps/shared/worldmap/tileLayer'

const props = defineProps<{
  /** True once the operator tried to save, so gaps may be pointed out. */
  saveAttempted: boolean
}>()

const form = defineModel<SettingsForm>('form', { required: true })

const emit = defineEmits<{ 'pick-view': [] }>()

const { _t } = usei18n()

const autoSourceOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('None — manual placement only') },
    { name: 'all_hosts', title: _t('All hosts with geo coordinates') },
    { name: 'hostgroup', title: _t('Hosts in host group…') },
    { name: 'servicegroup', title: _t('Hosts hosting a service in service group…') }
  ]
}))

const needsGroupName = computed(
  () =>
    form.value.worldmap_auto_source === 'hostgroup' ||
    form.value.worldmap_auto_source === 'servicegroup'
)
const groupNameMissing = computed(
  () => props.saveAttempted && !form.value.worldmap_auto_filter_value
)

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
        <EditField :label="_t('Latitude')">
          <CmkInput v-model="form.worldmap_lat" type="number" />
        </EditField>
        <EditField :label="_t('Longitude')">
          <CmkInput v-model="form.worldmap_lng" type="number" />
        </EditField>
        <EditField
          :label="_t('Zoom')"
          :help="_t('Pan/zoom the map first, then reopen settings to capture the current view.')"
        >
          <CmkInput v-model="form.worldmap_zoom" type="number" min="1" max="18" />
        </EditField>
      </div>
      <CmkButton
        variant="secondary"
        :title="_t('Closes settings and switches the map to picker mode.')"
        @click="emit('pick-view')"
      >
        <CmkIcon name="zoom" size="small" />
        <span>{{ _t('Pick from map') }}</span>
      </CmkButton>
    </div>

    <EditField
      :label="_t('Tile server URL')"
      :help="
        _t(
          'Leave empty for the site default. Only OpenStreetMap and the tile server configured in the global settings can be reached — tiles from anywhere else are blocked by the browser.'
        )
      "
    >
      <CmkInput
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
    <EditField :label="_t('Map saturation (%)')">
      <CmkInput
        v-model="form.worldmap_tile_saturate"
        type="number"
        :min="0"
        :max="100"
        :step="5"
        :placeholder="_t('100 (default)')"
      />
    </EditField>

    <EditField
      :label="_t('Automap source')"
      :help="
        _t(
          'Hosts are auto-discovered from monitoring data via maps_lat/maps_lng labels or LAT/LONG custom variables. They show up alongside any objects you place manually.'
        )
      "
    >
      <CmkDropdown
        :model-value="form.worldmap_auto_source"
        :options="autoSourceOptions"
        :label="_t('Automap source')"
        width="fill"
        @update:model-value="
          form.worldmap_auto_source = ($event ?? '') as typeof form.worldmap_auto_source
        "
      />
    </EditField>
    <EditField v-if="needsGroupName" :label="_t('Group name')" required>
      <CmkInput
        v-model="form.worldmap_auto_filter_value"
        :placeholder="_t('group name')"
        field-size="fill"
        :external-errors="groupNameMissing ? [_t('Pick a group to discover hosts from.')] : []"
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
