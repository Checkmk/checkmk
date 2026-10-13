<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Adding images to the library: a button in front of the file input it opens, so
the accepted file types are stated in one place and both the library view and
the picker offer the same upload.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useTemplateRef } from 'vue'

const { label, variant = 'primary' } = defineProps<{
  label: TranslatedString
  /** 'text' is the quiet variant for a footer; 'primary' heads a page. */
  variant?: 'primary' | 'text'
}>()

defineEmits<{ change: [event: Event] }>()

const fileInput = useTemplateRef<HTMLInputElement>('fileInput')
</script>

<template>
  <span class="maps-image-upload-button">
    <CmkButton
      :variant="variant"
      :icon="{ name: 'upload', size: 'small' }"
      @click="fileInput?.click()"
    >
      {{ label }}
    </CmkButton>
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/svg+xml,image/webp"
      multiple
      class="maps-image-upload-button__input"
      @change="$emit('change', $event)"
    />
  </span>
</template>

<style scoped>
.maps-image-upload-button__input {
  display: none;
}
</style>
