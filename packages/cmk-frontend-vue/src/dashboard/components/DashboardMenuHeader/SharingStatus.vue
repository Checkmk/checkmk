<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import StatusMessage, { type StatusType } from '../StatusMessage.vue'

const { _t } = usei18n()

export type SharingState = 'disabled' | 'paused' | 'active'

interface SharingStatusProps {
  sharingState: SharingState
  sharedUntil?: Date | null | undefined
}

interface SharingStatusEmits {
  openSharingSettings: []
}

const props = defineProps<SharingStatusProps>()
const emit = defineEmits<SharingStatusEmits>()

type SharingData = {
  status: StatusType
  text: TranslatedString
  linkedText: TranslatedString
}

const sharedData = computed((): SharingData => {
  if (props.sharingState === 'paused') {
    return {
      status: 'WARNING',
      text: _t('Sharing'),
      linkedText: _t('paused')
    }
  }

  if (props.sharingState === 'disabled') {
    return {
      status: 'DANGER',
      text: _t('Sharing'),
      linkedText: _t('disabled')
    }
  }

  if (!props.sharedUntil) {
    return {
      status: 'OK',
      text: _t('Sharing'),
      linkedText: _t('active')
    }
  }

  const getDate = () => (props.sharedUntil ? props.sharedUntil.toISOString().split('T')[0]! : '')

  const daysUntilExpired: number = Math.ceil(
    (props.sharedUntil.getTime() - new Date().getTime()) / (1000 * 3600 * 24)
  )

  if (daysUntilExpired > 7) {
    return {
      status: 'OK',
      text: _t('Sharing until'),
      linkedText: untranslated(getDate())
    }
  }

  if (daysUntilExpired > 1) {
    return {
      status: 'WARNING',
      text: _t('Sharing'),
      linkedText: _t('expires in %{days} days', { days: daysUntilExpired })
    }
  }

  if (daysUntilExpired === 1) {
    return {
      status: 'WARNING',
      text: _t('Sharing'),
      linkedText: _t('expires in 1 day')
    }
  }

  if (daysUntilExpired === 0) {
    return {
      status: 'WARNING',
      text: _t('Sharing'),
      linkedText: _t('expires today')
    }
  }

  return {
    status: 'DANGER',
    text: _t('Sharing expired on'),
    linkedText: untranslated(getDate())
  }
})
</script>

<template>
  <StatusMessage
    :status="sharedData.status"
    :text="sharedData.text"
    :linked-text="sharedData.linkedText"
    @click="emit('openSharingSettings')"
  />
</template>
