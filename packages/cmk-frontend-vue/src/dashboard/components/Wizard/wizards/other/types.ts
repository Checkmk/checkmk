/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { WidgetProps } from '../../types'

export enum OtherWidgetType {
  USER_MESSAGES = 'user_messages',
  SIDEBAR_WIDGET = 'sidebar_widget',
  EMBEDDED_URL = 'embedded_url',
  STATIC_TEXT = 'static_text'
}

export interface GetValidWidgetProps {
  getValidWidgetProps: () => WidgetProps | null
}
