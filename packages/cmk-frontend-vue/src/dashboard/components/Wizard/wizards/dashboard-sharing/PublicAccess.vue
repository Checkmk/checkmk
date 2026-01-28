<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Reactive, reactive, toRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkCatalogPanel from '@/components/CmkCatalogPanel.vue'
import CmkCode from '@/components/CmkCode.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import PopupDialog, { type PopupDialogProps } from '@/dashboard/components/PopupDialog.vue'
import type { DashboardFeatures, DashboardKey } from '@/dashboard/types/dashboard'
import { urlHandler } from '@/dashboard/utils'

import ContentSpacer from '../../components/ContentSpacer.vue'
import PublicAccessSettings from './PublicAccessSettings.vue'
import { type DashboardTokenModel } from './api'
import { usePublicAccess } from './composables/usePublicAccess'

const { _t } = usei18n()

interface PublicAccessLinkProps {
  dashboardKey: DashboardKey
  publicToken: DashboardTokenModel | null
  availableFeatures: DashboardFeatures
}

interface PublicAccessEmits {
  refreshDashboardSettings: []
}
const props = defineProps<PublicAccessLinkProps>()
const emit = defineEmits<PublicAccessEmits>()

const dialogData: Reactive<PopupDialogProps> = reactive({
  open: false,
  title: _t('Stop sharing public link?'),
  message: _t('This will disable the link and revoke access for all viewers.'),
  variant: 'warning',
  buttons: [{ title: _t('Enable access'), variant: 'warning', onclick: () => {} }]
})

const handler = usePublicAccess(
  props.dashboardKey.name,
  props.dashboardKey.owner,
  toRef(props, 'publicToken'),
  props.availableFeatures
)

const handleEnableAccess = async () => {
  if (!handler.runningUpdateTokenCall.value && handler.validate()) {
    dialogData.title = _t('Enable public link?')
    dialogData.message = [_t('Anyone with the link can view this dashboard.')]

    if (handler.validUntil.value) {
      const expiryDateStr = handler.validUntil.value.toISOString().split('T')[0]!
      dialogData.message.push(
        _t('Access will automatically expire on %{date}.', { date: expiryDateStr })
      )
    }

    dialogData.buttons = [
      {
        title: _t('Enable access'),
        variant: 'warning',
        onclick: async () => {
          dialogData.open = false
          handler.isDisabled.value = false
          await handler.updateToken()
          emit('refreshDashboardSettings')
        }
      }
    ]

    dialogData.open = true
  }
}

const handleDisableAccess = async () => {
  if (!handler.runningUpdateTokenCall.value && handler.validate()) {
    dialogData.title = _t('Stop sharing public link?')
    dialogData.message = _t('This will disable the link and revoke access for all viewers.')

    dialogData.buttons = [
      {
        title: _t('Disable access'),
        variant: 'warning',
        onclick: async () => {
          dialogData.open = false
          handler.isDisabled.value = true
          await handler.updateToken()
          emit('refreshDashboardSettings')
        }
      }
    ]

    dialogData.open = true
  }
}

const handleCreate = async () => {
  if (!handler.runningCreateTokenCall.value) {
    await handler.createToken()
    emit('refreshDashboardSettings')
  }
}

const handleDelete = () => {
  if (!handler.runningDeleteTokenCall.value) {
    dialogData.title = _t('Delete public link?')
    dialogData.message = _t('This will delete the link and revoke access for all viewers.')

    dialogData.buttons = [
      {
        title: _t('Delete public link?'),
        variant: 'warning',
        onclick: async () => {
          dialogData.open = false
          await handler.deleteToken()
          emit('refreshDashboardSettings')
        }
      }
    ]
    dialogData.open = true
  }
}

const handleUpdate = async () => {
  if (!handler.runningUpdateTokenCall.value && handler.validate()) {
    await handler.updateToken()
    emit('refreshDashboardSettings')
  }
}
</script>

<template>
  <CmkCatalogPanel :title="_t('Public access')" variant="padded">
    <CmkHeading type="h2">{{ _t('Anyone with this link can view the dashboard') }}</CmkHeading>
    <CmkLabel>{{ _t('Navigation and menus are hidden.') }}</CmkLabel>

    <ContentSpacer />

    <PopupDialog
      :open="dialogData.open"
      :title="dialogData.title"
      :message="dialogData.message"
      :buttons="dialogData.buttons"
      :variant="dialogData.variant"
      :dismissal_button="{ title: _t('Cancel'), key: 'cancel' }"
      @close="dialogData.open = false"
    />

    <CmkButton
      v-if="!publicToken"
      :class="{ 'shimmer-input-button': handler.runningCreateTokenCall.value }"
      @click="handleCreate"
      >{{ _t('Generate public link') }}</CmkButton
    >

    <template v-else>
      <CmkLabel>{{ _t('Public dashboard URL') }}</CmkLabel>
      <div class="db-public-access__row">
        <div class="db-public-access__cell db-public-access__overflow">
          <CmkCode :code_txt="urlHandler.getSharedDashboardLink(publicToken.token_id)" />
        </div>

        <div class="db-public-access__cell">
          <CmkButton
            v-if="publicToken.is_disabled"
            :class="{ 'shimmer-input-button': handler.runningUpdateTokenCall.value }"
            @click="handleEnableAccess"
            >{{ _t('Enable access') }}</CmkButton
          >

          <CmkButton
            v-else
            :class="{ 'shimmer-input-button': handler.runningUpdateTokenCall.value }"
            @click="handleDisableAccess"
            >{{ _t('Disable access') }}</CmkButton
          >
        </div>

        <div class="db-public-access__cell">
          <a href="#" @click="handleDelete">{{ _t('Delete') }}</a>
        </div>
      </div>
    </template>

    <template v-if="handler.isShared.value">
      <ContentSpacer variant="line" />
      <PublicAccessSettings
        v-model:has-validity="handler.hasValidity.value"
        v-model:valid-until="handler.validUntil.value"
        v-model:comment="handler.comment.value"
        :validate="handler.validate"
        :validation-error="handler.validationError.value"
        :available-features="availableFeatures"
        @update-settings="handleUpdate"
      />
    </template>
  </CmkCatalogPanel>
</template>

<style scoped>
.db-public-access__row {
  display: flex;
  flex-flow: row nowrap;
  place-content: flex-start space-between;
  align-items: baseline;
  width: 100%;
  gap: var(--dimension-5);
}

.db-public-access__cell {
  flex: 0;
  text-wrap: nowrap;
}

.db-public-access__cell:first-child {
  flex: 1;
}

.db-public-access__overflow {
  overflow-x: scroll;
}
</style>
