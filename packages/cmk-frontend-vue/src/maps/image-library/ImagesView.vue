<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The image library: the images an operator uploaded for their map objects and
backgrounds, plus the built-in ones. The only administration surface that stays
inside the SPA — connections and defaults live in Checkmk's global settings.

Heading and the upload are the Checkmk page menu ``maps.py`` renders above the
app (see ``shared/pageMenu.ts``).
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, useTemplateRef } from 'vue'

import ImageGrid from '@/maps/image-library/components/ImageGrid.vue'
import ImageUsageDialog from '@/maps/image-library/components/ImageUsageDialog.vue'
import { useImageDeletion } from '@/maps/image-library/composables/useImageDeletion'
import { useImageLibrary } from '@/maps/image-library/composables/useImageLibrary'
import { IMAGE_UPLOAD_ACCEPT } from '@/maps/image-library/upload'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'
import { onPageMenuAction } from '@/maps/shared/pageMenu'

const { _t } = usei18n()

const library = useImageLibrary()
const deletion = useImageDeletion(library.forget, library.reportError)

const fileInput = useTemplateRef<HTMLInputElement>('fileInput')
onPageMenuAction((action) => {
  if (action === 'upload') {
    fileInput.value?.click()
  }
})

const deleteTitle = computed(() =>
  deletion.target.value
    ? _t('Delete image "%{name}"?', { name: deletion.target.value })
    : untranslated('')
)
</script>

<template>
  <div class="maps-images-view">
    <!-- Opened by the page menu's "Upload image" entry. -->
    <input
      ref="fileInput"
      type="file"
      :accept="IMAGE_UPLOAD_ACCEPT"
      multiple
      class="maps-images-view__file-input"
      @change="library.uploadFiles"
    />

    <CmkAlert
      v-if="library.errorMessage.value"
      variant="error"
      :text="library.errorMessage.value"
    />

    <div v-if="library.loading.value" class="maps-images-view__loading">
      <CmkLoading />
    </div>

    <template v-else>
      <CmkSearchInput
        v-model="library.query.value"
        :placeholder="_t('Search images…')"
        class="maps-images-view__search"
      />

      <!-- The operator's own material first: it is the actionable part. -->
      <ImageGrid
        :title="_t('Uploaded images')"
        :images="library.matchingUploaded.value"
        :empty-hint="
          library.hasUploads.value
            ? undefined
            : _t('No images uploaded yet — upload one to add custom icons.')
        "
        :no-match-hint="_t('No matches for \'%{q}\'.', { q: library.query.value })"
        deletable
        @delete="deletion.start"
      />
      <ImageGrid
        :title="_t('Built-in icons')"
        :images="library.matchingBuiltin.value"
        :no-match-hint="_t('No matches for \'%{q}\'.', { q: library.query.value })"
      />
    </template>

    <MapsConfirmDialog
      :open="deletion.askedAboutUnused.value"
      variant="error"
      :title="deleteTitle"
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="deletion.confirm"
      @cancel="deletion.cancel"
    />
    <ImageUsageDialog
      :open="deletion.askedAboutUsed.value"
      :image-name="deletion.target.value ?? ''"
      :usage="deletion.usage.value"
      @confirm="deletion.confirm"
      @cancel="deletion.cancel"
    />
  </div>
</template>

<style scoped>
.maps-images-view {
  flex: 1;
  padding: var(--dimension-4) var(--dimension-4) var(--dimension-11);
  overflow: auto;
}

.maps-images-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-10) 0;
}

.maps-images-view__file-input {
  display: none;
}

.maps-images-view__search {
  max-width: 320px;
  margin-bottom: var(--dimension-6);
}
</style>
