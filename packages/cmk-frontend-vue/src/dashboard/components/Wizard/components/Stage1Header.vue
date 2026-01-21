<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from './ActionBar.vue'
import ActionButton from './ActionButton.vue'
import ContentSpacer from './ContentSpacer.vue'

const { _t } = usei18n()

interface Stage1HeaderEmits {
  click: []
}

interface Stage1HeaderProps {
  buttonTitle?: TranslatedString
}

defineProps<Stage1HeaderProps>()
const emit = defineEmits<Stage1HeaderEmits>()
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Data selection') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="buttonTitle || _t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      :action="() => emit('click')"
      variant="secondary"
    />
  </ActionBar>

  <ContentSpacer :dimension="11" />

  <CmkParagraph>
    {{ _t('Select the data you want to analyze') }} <br />
    {{ _t("Default filters apply here and don't have to be selected again") }}
  </CmkParagraph>

  <ContentSpacer :dimension="8" />
</template>
