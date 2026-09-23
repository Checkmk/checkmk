<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Who can see the map: only its owner, everyone, or the members of the contact
groups or sites picked here; and whether the Monitor menu links it.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { MapAccess, PublicMode } from '@/maps/map/edit/settings/useMapAccess'

const { access } = defineProps<{ access: MapAccess }>()

const { _t } = usei18n()
</script>

<template>
  <div class="maps-map-access-tab">
    <p class="maps-map-access-tab__intro">
      {{
        _t(
          'Control who can see this map and whether it is listed in the Monitor menu. You can always see your own maps.'
        )
      }}
    </p>

    <div class="maps-map-access-tab__field">
      <CmkLabel>{{ _t('Visibility') }}</CmkLabel>
      <CmkDropdown
        :model-value="access.mode.value"
        :options="access.modeOptions.value"
        :label="_t('Visibility')"
        width="fill"
        @update:model-value="access.setMode(($event as PublicMode) ?? 'private')"
      />
    </div>

    <div v-if="access.mode.value === 'groups'" class="maps-map-access-tab__field">
      <CmkLabel>{{ _t('Contact groups') }}</CmkLabel>
      <p v-if="access.groupChoices.value.length === 0" class="maps-map-access-tab__empty">
        {{ _t('No contact groups available to share with.') }}
      </p>
      <div v-else class="maps-map-access-tab__choices">
        <label
          v-for="group in access.groupChoices.value"
          :key="group.id"
          class="maps-map-access-tab__choice"
        >
          <CmkCheckbox
            :model-value="access.groups.value.includes(group.id)"
            @update:model-value="access.toggleGroup(group.id)"
          />
          <span>{{ group.alias }}</span>
        </label>
      </div>
    </div>

    <div v-if="access.mode.value === 'sites'" class="maps-map-access-tab__field">
      <CmkLabel>{{ _t('Sites') }}</CmkLabel>
      <p v-if="access.siteChoices.value.length === 0" class="maps-map-access-tab__empty">
        {{ _t('No sites available to share with.') }}
      </p>
      <div v-else class="maps-map-access-tab__choices">
        <label
          v-for="site in access.siteChoices.value"
          :key="site.id"
          class="maps-map-access-tab__choice"
        >
          <CmkCheckbox
            :model-value="access.sites.value.includes(site.id)"
            @update:model-value="access.toggleSite(site.id)"
          />
          <span>{{ site.alias }}</span>
        </label>
      </div>
    </div>

    <div class="maps-map-access-tab__field">
      <CmkLabel>{{ _t('Monitor menu') }}</CmkLabel>
      <CmkCheckbox
        :model-value="access.hideInMonitorMenu.value"
        :label="_t('Hide this map in the Monitor menu')"
        @update:model-value="access.setHideInMonitorMenu"
      />
    </div>

    <p v-if="access.cannotShare.value" class="maps-map-access-tab__note">
      {{ _t('You do not have permission to share maps with other users.') }}
    </p>
  </div>
</template>

<style scoped>
.maps-map-access-tab {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  max-width: 520px;
}

.maps-map-access-tab__intro {
  margin: 0;
  color: var(--font-color-dimmed);
}

.maps-map-access-tab__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.maps-map-access-tab__empty,
.maps-map-access-tab__note {
  margin: 0;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-map-access-tab__choices {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--dimension-3);
}

.maps-map-access-tab__choice {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
