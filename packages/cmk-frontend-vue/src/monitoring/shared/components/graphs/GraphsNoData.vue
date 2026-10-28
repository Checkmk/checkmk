<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from 'cmk-ui-library/components/CmkHtml.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{
  /** Whose graphs are missing. */
  subject: 'host' | 'service'
  /** Why there are no graphs, in the backend's words. Null for the general explanation. */
  message: string | null
}>()

const { _t } = usei18n()
</script>

<template>
  <CmkParagraph v-if="message === null">
    {{
      subject === 'host'
        ? _t('Checkmk has no graphs for this host.')
        : _t('Checkmk has no graphs for this service.')
    }}
  </CmkParagraph>
  <CmkHtml v-else :html="message" />
</template>
