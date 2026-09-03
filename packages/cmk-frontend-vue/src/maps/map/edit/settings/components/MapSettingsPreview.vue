<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map as the settings currently describe it, beside the form editing them.

It is the real view in an iframe rather than a mock-up, so what the operator
sees before saving is what the map will actually look like.
-->
<script setup lang="ts">
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { SettingsPreview } from '@/maps/map/edit/settings/useSettingsPreview'

const { preview } = defineProps<{ preview: SettingsPreview }>()

const { _t } = usei18n()
</script>

<template>
  <aside class="maps-map-settings-preview">
    <span class="maps-map-settings-preview__label">{{ _t('Live preview') }}</span>
    <div class="maps-map-settings-preview__stage">
      <!-- The frame itself is handed to the composable: it is what the
           patches are posted to. -->
      <iframe
        :ref="(el) => preview.attach(el as HTMLIFrameElement | null)"
        :src="preview.url.value"
        class="maps-map-settings-preview__frame"
        :title="_t('Live preview')"
        @load="preview.onLoaded"
      />
      <div v-if="preview.loading.value" class="maps-map-settings-preview__loading">
        <CmkLoading />
      </div>
    </div>
  </aside>
</template>

<style scoped>
.maps-map-settings-preview {
  position: sticky;
  top: 0;
  display: flex;
  flex: 1 1 40%;
  flex-direction: column;
  gap: var(--dimension-2);
  align-self: flex-start;
  min-width: 0;
  max-height: calc(100vh - 120px);
  padding-left: var(--dimension-4);
  border-left: 1px solid var(--default-border-color);
}

.maps-map-settings-preview__label {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}

.maps-map-settings-preview__stage {
  position: relative;
  display: flex;
  flex: 1;
}

.maps-map-settings-preview__frame {
  flex: none;
  width: 100%;
  aspect-ratio: 4 / 3;
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
}

.maps-map-settings-preview__loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--input-hover-bg-color);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
}
</style>
