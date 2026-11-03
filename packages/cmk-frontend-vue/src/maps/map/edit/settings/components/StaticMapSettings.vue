<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a static map is drawn on: a picture, a colour, or both.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import EditField from '@/maps/map/edit/components/EditField.vue'
import BackgroundImageUpload from '@/maps/map/edit/settings/components/BackgroundImageUpload.vue'
import SettingsSection from '@/maps/map/edit/settings/components/SettingsSection.vue'
import type { SettingsForm } from '@/maps/map/edit/settings/settingsForm'
import type { StagedBackgroundImage } from '@/maps/map/edit/settings/useStagedBackgroundImage'
import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'
import type { BackgroundPosition, BackgroundStyle } from '@/maps/types/api'

const props = defineProps<{
  background: StagedBackgroundImage
  /** The NagVis-compatible renderer, which always draws the image at its own size. */
  classic: boolean
}>()

const form = defineModel<SettingsForm>('form', { required: true })

const { _t } = usei18n()

const hasImage = computed(
  () =>
    !props.background.removed.value &&
    (!!form.value.background_image || props.background.file.value !== null)
)

const styleOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'single', title: _t('Original size') },
    { name: 'zoom', title: _t('Zoom to fit') },
    { name: 'stretch', title: _t('Stretch to fill') },
    { name: 'tile', title: _t('Tile') }
  ]
}))

const positionOptions = computed(() => [
  { label: _t('Top left'), value: 'top_left' },
  { label: _t('Center'), value: 'center' }
])
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
    <template v-if="hasImage && !classic">
      <EditField
        :label="_t('Image style')"
        :help="
          _t(
            'Original size uses the image\'s pixels as map coordinates, so objects stay where they were placed even when the map grows. Zoom to fit scales the image to the map without distorting it, Stretch to fill distorts it to the map\'s size, and Tile repeats it at its original size. The map as a whole always scales to the window.'
          )
        "
      >
        <CmkDropdown
          :model-value="form.background_style"
          :options="styleOptions"
          :label="_t('Image style')"
          width="fill"
          @update:model-value="form.background_style = ($event as BackgroundStyle) ?? 'single'"
        />
      </EditField>
      <EditField
        :label="_t('Image position')"
        :help="
          _t(
            'Top left keeps the map in the top left corner and extends it to the right or below to fill the window. Center keeps the map\'s proportions and centers it in the window, with the image centered on the map.'
          )
        "
      >
        <CmkToggleButtonGroup
          :model-value="form.background_position"
          :options="positionOptions"
          @update:model-value="form.background_position = $event as BackgroundPosition"
        />
      </EditField>
    </template>
    <EditField v-slot="{ id, label }" labels-control :label="_t('Background color')">
      <MapsColorInput
        v-model="form.background_color"
        :label="label"
        :input-id="id"
        :enable-label="_t('Use color')"
        default-color="#1f2937"
      />
    </EditField>
  </SettingsSection>
</template>
