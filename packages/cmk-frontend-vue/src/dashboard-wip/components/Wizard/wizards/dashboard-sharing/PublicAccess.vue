<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Reactive, reactive, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkCode from '@/components/CmkCode.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import PopupDialog, { type PopupDialogProps } from '@/dashboard-wip/components/PopupDialog.vue'
import { getSharedDashboardLink } from '@/dashboard-wip/utils'

import CollapsibleBox from '../../components/CollapsibleBox.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import PublicAccessSettings from './PublicAccessSettings.vue'
import { type DashboardTokenModel, createToken, deleteToken, updateToken } from './api'

const { _t } = usei18n()

interface PublicAccessLinkProps {
  dashboardName: string
  dashboardOwner: string
  publicToken: DashboardTokenModel | null
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

const comment = ref<string>(props.publicToken?.comment || '')
const expiresAt = ref<Date>(
  props.publicToken?.expires_at ? new Date(props.publicToken.expires_at) : new Date()
)

const waitAPICall = ref<boolean>(false)
const waitDeleteAPICall = ref<boolean>(false)

const handleEnableAccess = () => {
  if (waitAPICall.value) {
    return
  }

  dialogData.title = _t('Enable public link?')
  dialogData.message = [_t('Anyone with the link can view this dashboard.')]

  if (expiresAt.value) {
    const expiryDateStr = expiresAt.value.toISOString().split('T')[0]!
    dialogData.message.push(
      _t('Access will automatically expire on %{date}.', { date: expiryDateStr })
    )
  }

  dialogData.buttons = [
    {
      title: _t('Enable access'),
      variant: 'warning',
      onclick: () => {
        dialogData.open = false
        waitAPICall.value = true
        void updateToken(
          props.dashboardName,
          props.dashboardOwner,
          false,
          expiresAt.value ?? new Date(),
          comment.value
        ).then(() => {
          waitAPICall.value = false
          emit('refreshDashboardSettings')
        })
      }
    }
  ]

  dialogData.open = true
}

const handleDisableAccess = () => {
  if (waitAPICall.value) {
    return
  }

  dialogData.title = _t('Stop sharing public link?')
  dialogData.message = _t('This will disable the link and revoke access for all viewers.')

  dialogData.buttons = [
    {
      title: _t('Disable access'),
      variant: 'warning',
      onclick: () => {
        dialogData.open = false
        waitAPICall.value = true
        void updateToken(
          props.dashboardName,
          props.dashboardOwner,
          true,
          expiresAt.value ?? new Date(),
          comment.value
        ).then(() => {
          emit('refreshDashboardSettings')
          waitAPICall.value = false
        })
      }
    }
  ]

  dialogData.open = true
}

const handleUpdate = async (callback?: () => void) => {
  if (waitAPICall.value) {
    return
  }
  waitAPICall.value = true
  void updateToken(
    props.dashboardName,
    props.dashboardOwner,
    props.publicToken?.is_disabled,
    expiresAt.value ?? new Date(),
    comment.value
  ).then(() => {
    emit('refreshDashboardSettings')
    waitAPICall.value = false
    if (callback) {
      callback()
    }
  })
}

const handleCreate = async () => {
  if (waitAPICall.value) {
    return
  }

  waitAPICall.value = true

  await createToken(props.dashboardName!, props.dashboardOwner).then(() => {
    emit('refreshDashboardSettings')
    waitAPICall.value = false
  })
}

const handleDelete = () => {
  if (waitDeleteAPICall.value) {
    return
  }

  dialogData.title = _t('Delete public link?')
  dialogData.message = _t('This will delete the link and revoke access for all viewers.')

  dialogData.buttons = [
    {
      title: _t('Delete public link?'),
      variant: 'warning',
      onclick: async () => {
        dialogData.open = false

        waitDeleteAPICall.value = true

        await deleteToken(props.dashboardName!, props.dashboardOwner).then(() => {
          emit('refreshDashboardSettings')
          waitDeleteAPICall.value = false
        })
      }
    }
  ]

  dialogData.open = true
}
</script>

<template>
  <CollapsibleBox :title="_t('Public access')" :open="true">
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
      :class="{ 'shimmer-input-button': waitAPICall }"
      @click="handleCreate"
      >{{ _t('Generate public link') }}</CmkButton
    >

    <template v-else>
      <CmkLabel>{{ _t('Public dashboard URL') }}</CmkLabel>
      <div class="db-public-access__row">
        <div class="db-public-access__cell db-public-access__overflow">
          <CmkCode :code_txt="getSharedDashboardLink(publicToken.token_id)" />
        </div>

        <div class="db-public-access__cell">
          <CmkButton
            v-if="publicToken.is_disabled"
            :class="{ 'shimmer-input-button': waitAPICall }"
            @click="handleEnableAccess"
            >{{ _t('Enable access') }}</CmkButton
          >

          <CmkButton
            v-else
            :class="{ 'shimmer-input-button': waitAPICall }"
            @click="handleDisableAccess"
            >{{ _t('Disable access') }}</CmkButton
          >
        </div>

        <div class="db-public-access__cell">
          <a href="#" @click="handleDelete">{{ _t('Delete') }}</a>
        </div>
      </div>
    </template>

    <template v-if="!!publicToken">
      <ContentSpacer variant="line" />

      <PublicAccessSettings
        v-model:valid-until="expiresAt"
        v-model:comment="comment"
        @update-settings="handleUpdate"
      />
    </template>
  </CollapsibleBox>
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
