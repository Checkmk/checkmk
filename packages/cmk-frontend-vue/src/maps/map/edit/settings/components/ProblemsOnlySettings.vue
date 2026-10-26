<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Whether the map starts out showing only its objects with a problem. The
switch on the map is each viewer's own and is not saved.
-->
<script setup lang="ts">
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'

import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()
const labelId = useId()
</script>

<template>
  <SettingsSection :title="_t('Problems')">
    <!-- No <label> around the switch: its slider toggles itself, and a label
         would pass the click on to the hidden checkbox, switching it back. -->
    <span class="maps-problems-only-settings__toggle">
      <CmkSwitch v-model="form.problems_only" :aria-labelledby="labelId" />
      <span :id="labelId" @click="form.problems_only = !form.problems_only">
        {{ _t('Show only problems') }}
      </span>
    </span>
  </SettingsSection>
</template>

<style scoped>
.maps-problems-only-settings__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  font-size: var(--font-size-normal);
  color: var(--font-color);
  cursor: pointer;
}
</style>
