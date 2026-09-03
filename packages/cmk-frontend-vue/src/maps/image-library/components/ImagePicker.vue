<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Picking one image out of the site's library, wherever an editor needs one: a
disclosure that opens the searchable grid, and the picked name beside its
thumbnail once something is chosen.

The listing, the search and the upload are the image library's own
(``useImageLibrary``) — this only adds the picking.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import ImageUploadButton from '@/maps/image-library/components/ImageUploadButton.vue'
import { useImageLibrary } from '@/maps/image-library/composables/useImageLibrary'
import { assetUrl } from '@/maps/utils/assetUrl'

const props = defineProps<{
  modelValue: string
  /** Overrides the label shown while nothing is picked. */
  placeholder?: TranslatedString
  /** 'icon' (default) offers the built-in library too; 'image' does not —
   *  a 24px monochrome icon is no slide background. */
  kind?: 'icon' | 'image'
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { _t, _tn } = usei18n()

const { loading, query, errorMessage, matchingUploaded, matchingAll, uploadFiles } =
  useImageLibrary()

const isImageKind = computed(() => props.kind === 'image')
const emptyLabel = computed(() => props.placeholder ?? _t('Icon filename'))
const searchLabel = computed(() => (isImageKind.value ? _t('Search images…') : _t('Search icons…')))
const uploadLabel = computed(() => (isImageKind.value ? _t('Upload image') : _t('Upload icon')))

const open = ref(false)

const tiles = computed(() =>
  (isImageKind.value ? matchingUploaded.value : matchingAll.value).map((image) => ({
    name: image.name,
    url: assetUrl(image.url),
    // A monochrome SVG has to be inverted in a dark theme; a coloured bitmap
    // must not be.
    monochrome: image.name.endsWith('.svg')
  }))
)

const countLabel = computed(() => {
  const shown = tiles.value.length
  return isImageKind.value
    ? _tn('%{n} image', '%{n} images', shown, { n: shown })
    : _tn('%{n} icon', '%{n} icons', shown, { n: shown })
})

function select(name: string) {
  emit('update:modelValue', name)
  open.value = false
  query.value = ''
}
</script>

<template>
  <div class="maps-image-picker">
    <div v-if="modelValue" class="maps-image-picker__selected">
      <img
        :src="assetUrl(`images/${modelValue}`)"
        class="maps-image-picker__image maps-image-picker__image--selected"
        :class="{ 'maps-image-picker__image--monochrome': modelValue.endsWith('.svg') }"
        alt=""
      />
      <span class="maps-image-picker__selected-name">{{ modelValue }}</span>
      <CmkIconButton
        name="close"
        size="xsmall"
        :title="_t('Clear selected image')"
        :aria-label="_t('Clear selected image')"
        @click="$emit('update:modelValue', '')"
      />
    </div>

    <!-- Once something is picked, clearing it is the way back to the grid. -->
    <button
      v-else
      type="button"
      class="maps-image-picker__toggle"
      :aria-expanded="open"
      @click="open = !open"
    >
      <CmkIcon name="icons" size="small" />
      <span class="maps-image-picker__toggle-label">{{ emptyLabel }}</span>
      <CmkMultitoneIcon
        name="chevron-down"
        primary-color="font"
        size="xsmall"
        class="maps-image-picker__chevron"
        :class="{ 'maps-image-picker__chevron--open': open }"
        aria-hidden="true"
      />
    </button>

    <div v-if="open" class="maps-image-picker__panel">
      <div class="maps-image-picker__search">
        <CmkSearchInput v-model="query" :placeholder="searchLabel" />
      </div>

      <CmkLoading v-if="loading" />
      <p v-else-if="tiles.length === 0 && query" class="maps-image-picker__hint">
        {{ _t('No images match "%{q}"', { q: query }) }}
      </p>
      <p v-else-if="tiles.length === 0" class="maps-image-picker__hint">
        {{ _t('No images uploaded yet') }}
      </p>
      <div v-else class="maps-image-picker__grid">
        <button
          v-for="tile in tiles"
          :key="tile.name"
          type="button"
          class="maps-image-picker__tile"
          :class="{ 'maps-image-picker__tile--selected': modelValue === tile.name }"
          :title="tile.name"
          @click="select(tile.name)"
        >
          <img
            :src="tile.url"
            :alt="tile.name"
            class="maps-image-picker__image"
            :class="{ 'maps-image-picker__image--monochrome': tile.monochrome }"
          />
          <span class="maps-image-picker__tile-name">{{ tile.name }}</span>
        </button>
      </div>

      <div class="maps-image-picker__footer">
        <span class="maps-image-picker__count">{{ countLabel }}</span>
        <ImageUploadButton :label="uploadLabel" variant="text" @change="uploadFiles" />
      </div>
      <p v-if="errorMessage" class="maps-image-picker__error">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<style scoped>
.maps-image-picker > * + * {
  margin-top: var(--dimension-4);
}

.maps-image-picker__selected {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 50%, transparent);
}

.maps-image-picker__selected-name {
  flex: 1;
  overflow: hidden;
  font-family: monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-image-picker__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-normal);
  line-height: 16px;
  text-align: left;
  background: var(--default-form-element-bg-color);
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.maps-image-picker__toggle:focus-visible {
  outline: revert;
}

.maps-image-picker__toggle-label {
  color: var(--font-color-dimmed);
}

.maps-image-picker__chevron {
  margin-left: auto;
  transition: transform 0.15s;
}

.maps-image-picker__chevron--open {
  transform: rotate(180deg);
}

.maps-image-picker__panel {
  overflow: hidden;
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-image-picker__search {
  padding: var(--dimension-4);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-image-picker__hint {
  margin: 0;
  padding: var(--dimension-7) 0;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  text-align: center;
}

.maps-image-picker__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--dimension-3);
  max-height: 208px;
  padding: var(--dimension-4);
  overflow-y: auto;
}

.maps-image-picker__tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3);
  border-radius: var(--border-radius);
}

.maps-image-picker__tile:hover {
  background: var(--input-hover-bg-color);
}

.maps-image-picker__tile--selected {
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.maps-image-picker__image {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  object-fit: contain;
}

/* A monochrome SVG loaded as <img> loses currentColor; inverting turns its
   black strokes light without touching coloured artwork. */
body[data-theme='modern-dark'] .maps-image-picker__image--monochrome {
  filter: invert(100%);
}

.maps-image-picker__tile-name {
  width: 100%;
  overflow: hidden;
  font-family: monospace;
  font-size: var(--font-size-small);
  line-height: 1.25;
  color: var(--font-color-dimmed);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-image-picker__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--dimension-4);
  border-top: 1px solid var(--default-border-color);
}

.maps-image-picker__count {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-image-picker__error {
  margin: 0;
  padding: 0 var(--dimension-4) var(--dimension-4);
  font-size: var(--font-size-normal);
  color: var(--color-light-red-40);
}
</style>
