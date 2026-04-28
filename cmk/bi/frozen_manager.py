#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.bi.storage import FrozenAggregationStore, Identifier, LookupStore
from cmk.bi.trees import (
    BICompiledAggregation,
    BICompiledRule,
    FrozenBIInfo,
    get_compiled_aggregation_and_branch_by_name,
)


class BIFrozenManager:
    def __init__(self, *, store: FrozenAggregationStore, lookup_store: LookupStore) -> None:
        self._frozen_store = store
        self._lookup_store = lookup_store

    def update(
        self, compiled_aggregations: dict[str, BICompiledAggregation]
    ) -> dict[str, BICompiledAggregation]:
        updated_aggregations = {}
        new_branch_was_frozen = False

        for aggr_id, compiled_aggregation in compiled_aggregations.items():
            updated_aggregations[aggr_id] = compiled_aggregation

            if compiled_aggregation.frozen_info is not None:
                continue  # Aggregation is already frozen.

            if not compiled_aggregation.computation_options.freeze_aggregations:
                self._frozen_store.delete(aggr_id)
                continue  # Aggregation is no longer frozen.

            new_branch_was_frozen = (
                self._freeze_new_branches(compiled_aggregation, compiled_aggregations)
                or new_branch_was_frozen
            )

            # Read frozen branches. Each branch gets a separate aggregation ID since
            # the computation time may differ, which also means possibly changed computation options
            for branch in list(compiled_aggregation.branches):
                branch_title = branch.properties.title
                if frozen_agg := self._frozen_store.get(compiled_aggregation.id, branch_title):
                    frozen_agg.frozen_info = FrozenBIInfo(compiled_aggregation.id, branch_title)
                    updated_aggregations[frozen_agg.id] = frozen_agg

            # Remove all branches from the original aggregation, since all of them are now frozen
            compiled_aggregation.branches = []

        if new_branch_was_frozen:
            self._lookup_store.generate_aggregation_lookups(updated_aggregations)

        return updated_aggregations

    def delete(self, identifier: Identifier) -> None:
        self._frozen_store.delete_by_identifier(identifier)

    def _freeze_new_branches(
        self,
        compiled_aggregation: BICompiledAggregation,
        compiled_aggregations: Mapping[str, BICompiledAggregation],
    ) -> bool:
        new_branch_found = False
        for branch in list(compiled_aggregation.branches):
            if self._frozen_store.exists(compiled_aggregation.id, branch.properties.title):
                continue  # Branch is already frozen.

            new_branch_found = True
            aggregation, branch = get_compiled_aggregation_and_branch_by_name(
                compiled_aggregations=compiled_aggregations,
                aggr_name=branch.properties.title,
            )
            self._freeze_branch(aggregation, branch)

        return new_branch_found

    def _freeze_branch(self, aggregation: BICompiledAggregation, branch: BICompiledRule) -> None:
        # Prepare a single frozen configuration specifically for this branch
        # This includes the aggregation configuration and the frozen branch
        if frozen_info := aggregation.frozen_info:
            aggr_id = frozen_info.based_on_aggregation_id
        else:
            aggr_id = aggregation.id

        branch_name = branch.properties.title
        original_branches = aggregation.branches
        original_id = aggregation.id

        try:
            aggregation.branches = [branch]
            aggregation.id = f"frozen_{aggr_id}_{branch_name}"
            self._frozen_store.save(aggregation, aggr_id, branch_name)
        finally:
            aggregation.branches = original_branches
            aggregation.id = original_id
