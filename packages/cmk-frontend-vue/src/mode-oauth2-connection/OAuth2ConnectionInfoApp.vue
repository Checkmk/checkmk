<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()
</script>

<template>
  <CmkAlert
    variant="info"
    :heading="_t('Microsoft Entra ID connections are only used by email checks')"
    :text="
      _t(
        'A connection configured here only creates an OAuth2 token that the Check email, Check email delivery and Check mailboxes active checks use to authenticate against Microsoft 365 mailboxes. It is not a general-purpose identity provider or single sign-on connection.'
      )
    "
  />
</template>
