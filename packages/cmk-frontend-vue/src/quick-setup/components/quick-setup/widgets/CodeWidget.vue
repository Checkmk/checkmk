<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { CodeWidgetProps } from './widget_types'

const props = defineProps<CodeWidgetProps>()
const { _t } = usei18n()
const downloadUrl = computed(() =>
  props.download_filename
    ? `data:text/plain;charset=utf-8,${encodeURIComponent(props.code)}`
    : undefined
)
</script>

<template>
  <div class="qs-code-widget">
    <CmkHeading v-if="download_filename" type="h4" class="qs-code-widget__filename">
      {{ title || download_filename }}
    </CmkHeading>
    <CmkCode
      v-bind="download_filename ? {} : { title }"
      :code-text="code"
      width="fill"
      :collapsible="false"
      wrap
    />
    <CmkButton v-if="downloadUrl" :href="downloadUrl" :download="download_filename ?? undefined">
      {{ _t('Download') }}
    </CmkButton>
  </div>
</template>

<style scoped>
.qs-code-widget {
  margin-bottom: var(--spacing);
}

.qs-code-widget__filename {
  margin-top: var(--dimension-5);
  font-family: monospace;
}
</style>
