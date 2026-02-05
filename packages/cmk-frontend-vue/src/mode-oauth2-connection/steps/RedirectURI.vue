<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'

import usei18n from '@/lib/i18n'

import CmkCode from '@/components/CmkCode.vue'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { buildRedirectUri } from './utils'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & {
    urls: Oauth2Urls
  }
>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Add redirect URI') }}</CmkHeading>
    </template>

    <template #content>
      {{
        _t(
          'Open the Redirect URIs or navigate to the Authentication settings and register the following Web redirect URI'
        )
      }}
      <CmkCode :code_txt="buildRedirectUri(props.urls.redirect)" />
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
