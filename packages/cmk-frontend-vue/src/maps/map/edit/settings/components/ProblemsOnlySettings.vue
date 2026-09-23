<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Whether the map shows only its objects with a problem. The switch on the map
itself sets the same field, so the form shows what the map currently shows.
-->
<script setup lang="ts">
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()
</script>

<template>
  <SettingsSection :title="_t('Problems')">
    <!-- .stop on the switch: the slider toggles itself, and the wrapping label
         would forward a second click to the hidden checkbox. -->
    <label class="maps-problems-only-settings__toggle">
      <CmkSwitch v-model="form.problems_only" @click.stop />
      <span>{{ _t('Show only problems') }}</span>
    </label>
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
