<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a static map is drawn on: a picture, a colour, or both.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import EditField from '@/maps/map/edit/components/EditField.vue'
import BackgroundImageUpload from '@/maps/map/edit/settings/components/BackgroundImageUpload.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'
import type { StagedBackgroundImage } from '@/maps/map/edit/settings/useStagedBackgroundImage'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'

defineProps<{ background: StagedBackgroundImage }>()

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()
</script>

<template>
  <SettingsSection :title="_t('Background')">
    <EditField :label="_t('Background image')">
      <BackgroundImageUpload
        :pending-file="background.file.value"
        :pending-remove="background.removed.value"
        :model-value="form.background_image"
        :pending-preview-url="background.previewUrl.value"
        @update:pending-file="background.pick($event)"
        @update:pending-remove="background.setRemoved($event)"
      />
    </EditField>
    <EditField :label="_t('Background color')">
      <MapsColorInput
        v-model="form.background_color"
        :enable-label="_t('Use color')"
        default-color="#1f2937"
      />
    </EditField>
  </SettingsSection>
</template>
