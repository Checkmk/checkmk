<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A section of the image library: its heading, and the images in it as tiles.
Uploaded images can be deleted, built-in ones cannot, which is the only
difference between the two sections.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { ImageEntry } from '@/maps/types/api'
import { assetUrl } from '@/maps/utils/assetUrl'

const props = defineProps<{
  title: TranslatedString
  images: ImageEntry[]
  /** Shown instead of the grid when the section itself holds nothing. */
  emptyHint?: TranslatedString | undefined
  /** Shown when the section has images but the search matched none. */
  noMatchHint?: TranslatedString | undefined
  deletable?: boolean | undefined
}>()

defineEmits<{ delete: [name: string] }>()

const { _t } = usei18n()

/**
 * The url and the invert flag follow from fields that never change, so they are
 * resolved once per listing rather than on every render — a keystroke in the
 * search box re-renders the whole grid.
 */
const tiles = computed(() =>
  props.images.map((image) => ({
    name: image.name,
    // What the caption shows. The extension is a fact about the file, not about
    // the icon, and it is the part an ellipsis eats into first -- 84 built-ins
    // all ending in ".svg" turned the row of captions into "device-desktop.…".
    // The full file name stays in the tooltip and in the label a screen reader
    // reads, because that is the name the rest of the UI refers to it by.
    label: image.name.replace(/\.[^.]+$/, ''),
    url: assetUrl(image.url),
    // A monochrome SVG has to be inverted in a dark theme; a coloured bitmap
    // must not be.
    monochrome: image.name.endsWith('.svg')
  }))
)
</script>

<template>
  <section class="maps-image-grid">
    <CmkHeading type="h3" class="maps-image-grid__title">
      {{ props.title }} ({{ props.images.length }})
    </CmkHeading>
    <p v-if="props.emptyHint" class="maps-image-grid__hint">{{ props.emptyHint }}</p>
    <p v-else-if="props.images.length === 0" class="maps-image-grid__hint">
      {{ props.noMatchHint }}
    </p>
    <div v-else class="maps-image-grid__tiles">
      <div v-for="tile in tiles" :key="tile.name" class="maps-image-grid__tile">
        <img
          :src="tile.url"
          :alt="tile.name"
          class="maps-image-grid__image"
          :class="{ 'maps-image-grid__image--monochrome': tile.monochrome }"
        />
        <p class="maps-image-grid__name" :title="tile.name">{{ tile.label }}</p>
        <CmkIconButton
          v-if="props.deletable"
          name="delete"
          size="xsmall"
          class="maps-image-grid__delete"
          :title="_t('Delete image')"
          :aria-label="_t('Delete image %{name}', { name: tile.name })"
          @click="$emit('delete', tile.name)"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.maps-image-grid {
  margin-bottom: var(--dimension-7);
}

.maps-image-grid__title {
  margin-bottom: var(--dimension-4);
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-image-grid__hint {
  margin: 0;
  padding: var(--dimension-5) 0;
  color: var(--font-color-dimmed);
}

.maps-image-grid__tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--dimension-4);
}

.maps-image-grid__tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-4);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px var(--default-border-color);
  transition: box-shadow 0.15s;
}

.maps-image-grid__tile:hover {
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.maps-image-grid__image {
  width: 40px;
  height: 40px;
  object-fit: contain;
}

/* A monochrome SVG loaded as <img> loses currentColor; inverting turns its
   black strokes white where the theme is dark. */
body[data-theme='modern-dark'] .maps-image-grid__image--monochrome {
  filter: invert(1);
}

.maps-image-grid__name {
  width: 100%;
  margin: 0;
  overflow: hidden;
  font-family: monospace;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-image-grid__delete {
  position: absolute;
  top: var(--dimension-3);
  right: var(--dimension-3);
  opacity: 0;
  transition: opacity 0.15s;
}

.maps-image-grid__delete:focus-visible,
.maps-image-grid__tile:hover .maps-image-grid__delete {
  opacity: 1;
}
</style>
