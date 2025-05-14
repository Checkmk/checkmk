/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated via the cmk-shared-typing package.
 * Do not edit manually.
 */

export interface DialogWithSlideinTypeDefs {
  agent_download?: AgentDownload;
}
export interface AgentDownload {
  url: string;
  i18n: AgentDownloadI18N;
}
export interface AgentDownloadI18N {
  dialog_title: string;
  dialog_message: string;
  slide_in_title: string;
  slide_in_button_title: string;
  docs_button_title: string;
}
