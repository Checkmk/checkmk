<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { assetUrl } from '@/maps/utils/assetUrl'

const ACCEPT_TYPES = 'image/png,image/jpeg,image/svg+xml,image/webp,image/gif'

const { _t } = usei18n()

const props = defineProps<{
  // Filename of the background already persisted on the server (display base).
  modelValue: string
  // Staged selection: uploaded/deleted only when the parent saves the map.
  pendingFile: File | null
  pendingRemove: boolean
  // data: URL of the staged file, provided by the parent. A data: URL (not a
  // blob:) is required because Checkmk's CSP allows ``img-src ... data:`` but
  // not blob:, so a blob: thumbnail would be silently blocked on OMD sites.
  pendingPreviewUrl?: string | null
}>()
const emit = defineEmits<{
  'update:pendingFile': [value: File | null]
  'update:pendingRemove': [value: boolean]
}>()

const cacheBust = ref(Date.now())
const previewFailed = ref(false)

watch(
  () => props.pendingFile,
  () => {
    previewFailed.value = false
  }
)
watch(
  () => props.modelValue,
  () => {
    previewFailed.value = false
    cacheBust.value = Date.now()
  }
)

const hasImage = computed(() =>
  props.pendingFile ? true : props.pendingRemove ? false : !!props.modelValue
)
const displayUrl = computed(() =>
  props.pendingFile
    ? (props.pendingPreviewUrl ?? '')
    : assetUrl(`maps/backgrounds/${props.modelValue}?v=${cacheBust.value}`)
)
const displayName = computed(() => props.pendingFile?.name ?? props.modelValue)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) {
    return
  }
  emit('update:pendingRemove', false)
  emit('update:pendingFile', file)
}

function removeOrCancel() {
  if (props.pendingFile) {
    // Undo the staged pick, falling back to the persisted image.
    emit('update:pendingFile', null)
    return
  }
  emit('update:pendingRemove', true)
}
</script>

<template>
  <div class="maps-background-image-upload">
    <div v-if="hasImage" class="maps-background-image-upload__preview">
      <img
        v-if="!previewFailed && displayUrl"
        :src="displayUrl"
        class="maps-background-image-upload__thumb"
        @error="previewFailed = true"
      />
      <div v-else-if="previewFailed" class="maps-background-image-upload__thumb-fallback">?</div>
      <span class="maps-background-image-upload__name">
        {{ displayName }}
        <span v-if="pendingFile" class="maps-background-image-upload__unsaved">
          · {{ _t('unsaved') }}
        </span>
      </span>
      <label class="maps-background-image-upload__replace">
        {{ _t('Replace…') }}
        <input
          type="file"
          :accept="ACCEPT_TYPES"
          class="maps-background-image-upload__file-input"
          @change="onFileChange"
        />
      </label>
      <button
        type="button"
        class="maps-background-image-upload__remove"
        :title="pendingFile ? _t('Cancel') : _t('Remove background image')"
        @click="removeOrCancel"
      >
        <CmkIcon name="close" size="small" />
      </button>
    </div>

    <label v-else class="maps-background-image-upload__upload">
      <CmkIcon name="upload" size="small" />
      {{ _t('Upload background image…') }}
      <input
        type="file"
        :accept="ACCEPT_TYPES"
        class="maps-background-image-upload__file-input"
        @change="onFileChange"
      />
    </label>
  </div>
</template>

<style scoped>
.maps-background-image-upload > * + * {
  margin-top: var(--dimension-4);
}

.maps-background-image-upload__preview {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 50%, transparent);
}

.maps-background-image-upload__thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: var(--border-radius);
}

.maps-background-image-upload__thumb-fallback {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  background: var(--input-hover-bg-color);
  border-radius: var(--border-radius);
}

.maps-background-image-upload__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-background-image-upload__unsaved {
  color: var(--font-color-dimmed);
}

.maps-background-image-upload__replace {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  font-size: 11px;
  color: var(--font-color-dimmed);
  cursor: pointer;
  border-radius: 6px;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.maps-background-image-upload__replace:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-background-image-upload__file-input {
  display: none;
}

.maps-background-image-upload__remove {
  color: var(--font-color-dimmed);
  transition: color 0.15s;
}

.maps-background-image-upload__remove:hover {
  color: var(--color-light-red-40);
}

.maps-background-image-upload__upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color-dimmed);
  cursor: pointer;
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
  transition: all 0.15s;
}

.maps-background-image-upload__upload:hover {
  color: var(--font-color);
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.maps-background-image-upload__upload:focus-within {
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}
</style>
