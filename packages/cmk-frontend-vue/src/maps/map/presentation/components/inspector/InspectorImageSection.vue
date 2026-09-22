<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ImagePicker from '@/maps/image-library/components/ImagePicker.vue'
import type { ImageElement } from '@/maps/types/api'

import { imageRefName } from '../../elements'

const { _t } = usei18n()

const props = defineProps<{ element: ImageElement }>()
const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Image src is either an image-store filename (bare name) or an external URL.
// The picker reflects only store images; the URL field only external ones.
const storeImageName = computed(() => imageRefName(props.element.src))
const externalSrc = computed(() => {
  const src = props.element.src ?? ''
  return imageRefName(src) ? '' : src
})

// A dropdown rather than a toggle group: the inspector column is 280px and
// CmkToggleButtonGroup is the form-scale control (150px per option), so three
// options wrap onto two rows.
const fitOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'contain', title: _t('Contain') },
    { name: 'cover', title: _t('Cover') },
    { name: 'fill', title: _t('Fill') }
  ]
}))

function onUrlChange(e: Event): void {
  emit('patch', { src: (e.target as HTMLInputElement).value || null })
}
</script>

<template>
  <section class="maps-inspector-image-section">
    <h3 class="maps-section-title">{{ _t('Image') }}</h3>
    <div class="maps-inspector-image-section__field">
      <span class="maps-cap">{{ _t('From image library') }}</span>
      <ImagePicker
        :model-value="storeImageName"
        :placeholder="_t('Choose an image…')"
        @update:model-value="emit('patch', { src: $event || null })"
      />
    </div>
    <div class="maps-inspector-image-section__field">
      <span class="maps-cap">{{ _t('…or image URL') }}</span>
      <input
        class="maps-field"
        :value="externalSrc"
        :placeholder="_t('https://…')"
        @change="onUrlChange"
      />
    </div>
    <div class="maps-inspector-image-section__field">
      <span class="maps-cap">{{ _t('Fit') }}</span>
      <CmkDropdown
        :model-value="element.fit"
        :options="fitOptions"
        :label="_t('Fit')"
        width="fill"
        @update:model-value="emit('patch', { fit: $event })"
      />
    </div>
  </section>
</template>

<style scoped>
.maps-inspector-image-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.maps-inspector-image-section__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
