<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The image library: the images an operator uploaded for their map objects and
backgrounds, plus the built-in ones. The only administration surface that stays
inside the SPA — connections and defaults live in Checkmk's global settings.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ImageGrid from '@/maps/image-library/components/ImageGrid.vue'
import ImageUploadButton from '@/maps/image-library/components/ImageUploadButton.vue'
import ImageUsageDialog from '@/maps/image-library/components/ImageUsageDialog.vue'
import { useImageDeletion } from '@/maps/image-library/composables/useImageDeletion'
import { useImageLibrary } from '@/maps/image-library/composables/useImageLibrary'
import { useNavigation } from '@/maps/services/context'
import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'

const { _t } = usei18n()
const nav = useNavigation()

const library = useImageLibrary()
const deletion = useImageDeletion(library.forget, library.reportError)

const breadcrumbItems = computed<BreadcrumbItem[]>(() => [
  { title: _t('Maps'), link: nav.href({ view: 'home' }) },
  { title: _t('Images'), link: null }
])

const deleteTitle = computed(() =>
  deletion.target.value
    ? _t('Delete image "%{name}"?', { name: deletion.target.value })
    : untranslated('')
)
</script>

<template>
  <div class="maps-images-view">
    <!-- The SPA's own breadcrumb: maps.py renders no server chrome, so this is
         the way back to the list. -->
    <CmkBreadcrumb :items="breadcrumbItems" class="maps-images-view__breadcrumb" />

    <div class="maps-images-view__header">
      <div>
        <CmkHeading type="h2">{{ _t('Images') }}</CmkHeading>
        <CmkParagraph class="maps-images-view__subtitle">
          {{ _t('Upload and manage images for map objects') }}
        </CmkParagraph>
      </div>
      <ImageUploadButton :label="_t('Upload image')" @change="library.uploadFiles" />
    </div>

    <CmkAlertBox v-if="library.errorMessage.value" variant="error">
      {{ library.errorMessage.value }}
    </CmkAlertBox>

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
  padding: var(--dimension-7) var(--dimension-8);
  overflow: auto;
}

.maps-images-view__breadcrumb {
  margin-bottom: var(--dimension-6);
}

.maps-images-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-6);
}

.maps-images-view__subtitle {
  margin-top: var(--dimension-3);
  color: var(--font-color-dimmed);
}

.maps-images-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-10) 0;
}

.maps-images-view__search {
  max-width: 320px;
  margin-bottom: var(--dimension-6);
}
</style>
