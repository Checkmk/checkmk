<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkCode from '@/components/CmkCode.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const codeText = ``
</script>

<template>
  <CmkParagraph>
    {{
      _t('Download the Relay container image and run it in your environment to start the setup.')
    }}
  </CmkParagraph>
  <CmkCode :code_txt="codeText"> </CmkCode>
</template>
