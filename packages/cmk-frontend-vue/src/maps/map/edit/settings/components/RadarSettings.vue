<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A radar map has no placed objects — what it shows follows from this filter,
resolved live against the connection.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'
import MapsObjectField from '@/maps/shared/components/MapsObjectField.vue'
import type { RadarView } from '@/maps/types/api'

const props = defineProps<{ saveAttempted: boolean }>()

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()

const filterOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'hostgroup', title: _t('Host group') },
    { name: 'servicegroup', title: _t('Service group') },
    { name: 'all_hosts', title: _t('All hosts') },
    { name: 'all_services', title: _t('All services') }
  ]
}))

const groupKind = computed(() =>
  form.value.radar_filter === 'hostgroup' || form.value.radar_filter === 'servicegroup'
    ? form.value.radar_filter
    : null
)

const groupNameMissing = computed(() => props.saveAttempted && !form.value.radar_filter_value)

// A group picked for the other kind of group must not survive the swap; a
// detour over a choice without a group keeps it.
let pickedFor = groupKind.value
watch(groupKind, (kind) => {
  if (kind === null) {
    return
  }
  if (pickedFor !== null && kind !== pickedFor) {
    form.value.radar_filter_value = ''
  }
  pickedFor = kind
})
</script>

<template>
  <SettingsSection :title="_t('Filter')">
    <EditField :label="_t('Filter type')">
      <CmkDropdown
        :model-value="form.radar_filter"
        :options="filterOptions"
        :label="_t('Filter type')"
        width="fill"
        @update:model-value="
          form.radar_filter = ($event as RadarView['filter'] | null) ?? 'hostgroup'
        "
      />
    </EditField>
    <EditField
      v-if="groupKind"
      :label="_t('Group name')"
      required
      :help="
        _t(
          'Hosts (or hosts hosting a service) belonging to this Checkmk group are pulled live from the connection. The group has to exist in the Checkmk setup.'
        )
      "
    >
      <CmkInlineValidation
        :validation="
          groupNameMissing ? [_t('Pick a group — the map has nothing to show without one.')] : []
        "
      />
      <MapsObjectField
        v-model="form.radar_filter_value"
        :kind="groupKind"
        :label="_t('Group name')"
        :placeholder="_t('Group name')"
        :has-error="groupNameMissing"
      />
    </EditField>
  </SettingsSection>
</template>
