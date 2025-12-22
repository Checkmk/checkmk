/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export enum ViewSelectionMode {
  NEW = 'new',
  COPY = 'copy',
  LINK = 'link'
}

export interface NewViewSelection {
  type: ViewSelectionMode.NEW
  datasource: string
  restrictedToSingle: string[]
}

export interface CopyExistingViewSelection {
  type: ViewSelectionMode.COPY
  viewName: string
}

export interface LinkExistingViewSelection {
  type: ViewSelectionMode.LINK
  viewName: string
}

export type ViewSelection = NewViewSelection | CopyExistingViewSelection | LinkExistingViewSelection

export enum DataConfigurationMode {
  CREATE = 'create',
  EDIT = 'edit'
}
