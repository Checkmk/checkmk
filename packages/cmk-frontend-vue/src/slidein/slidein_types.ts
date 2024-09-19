/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Catalog } from '@/form/components/vue_formspec_components'

export interface SlideInProps {
  id: string
  /** @property {string} save_button_label - The label for the save button  */
  save_button_label: string
  /** @property {string} cancel_button_label - The label for the cancel button */
  cancel_button_label: string
  /** @property {string} trigger_text - The label for the cancel button */
  trigger_text: string
  /** @property {Catalog} catalog - The content of the slide-in only supporting the catalog form (at the moment) */
  catalog: Catalog
  /** @property {string} description - The description of the slide-in */
  description?: string
}
