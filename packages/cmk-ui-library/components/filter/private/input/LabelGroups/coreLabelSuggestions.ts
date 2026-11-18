/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import { suggestFromAutocompleter } from 'cmk-ui-library/components/FormAutocompleter/suggestFromAutocompleter'

import type { LabelQueryBuilderConfig } from '../../../types.ts'

/** The labels that the monitoring core knows for one object type. */
export function suggestCoreLabels(
  objectType: LabelQueryBuilderConfig['object_type']
): QuerySuggestionsFn {
  return (query) =>
    suggestFromAutocompleter(
      {
        fetch_method: 'rest_autocomplete',
        data: {
          ident: 'label',
          params: { world: 'core', object_type: objectType, strict: true, escape_regex: false }
        }
      },
      query
    )
}
