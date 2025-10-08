"""Utilities for enriching cluster assignments with taxonomy metadata."""

from __future__ import annotations

import pandas as pd

from nanana.lib.taxon import name as fetch_taxon_name


def _top_taxid_per_read(
    read_taxon_df: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    """Return the best-supported taxid and its score for each read."""

    numeric_scores = read_taxon_df.apply(pd.to_numeric, errors="coerce")
    filled_scores = numeric_scores.where(numeric_scores.notna(), float("-inf"))
    top_taxids = filled_scores.idxmax(axis=1)
    max_scores = filled_scores.max(axis=1)
    valid_mask = max_scores > float("-inf")
    top_taxids = top_taxids[valid_mask].astype(str)
    max_scores = max_scores[valid_mask]
    return top_taxids, max_scores


def hydrate_clusters(
    cluster_df: pd.DataFrame,
    read_taxon_df: pd.DataFrame,
) -> pd.DataFrame:
    """Attach per-read taxonomy metadata."""

    required_columns = {"seq_name"}
    missing_columns = required_columns.difference(cluster_df.columns)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"Cluster table is missing required columns: {columns}.")

    read_ids = cluster_df["seq_name"].dropna().unique()
    if len(read_ids) == 0:
        raise ValueError("No reads available to annotate.")

    taxon_slice = read_taxon_df.reindex(read_ids)
    if taxon_slice.isna().all(axis=None):
        raise ValueError("Read-to-taxonomy matrix contains no usable assignments.")

    top_taxids, top_scores = _top_taxid_per_read(taxon_slice)
    if top_taxids.empty:
        raise ValueError("Unable to determine taxonomy for any reads with provided distances.")

    taxname_df = fetch_taxon_name(ids=sorted(top_taxids.unique()))
    taxname_df["TaxID"] = taxname_df["TaxID"].astype(str)
    id_to_name = dict(zip(taxname_df["TaxID"], taxname_df["Name"]))

    annotated_reads = cluster_df.copy()
    annotated_reads["TaxID"] = annotated_reads["seq_name"].map(top_taxids)
    annotated_reads["name"] = annotated_reads["TaxID"].map(id_to_name)
    annotated_reads["confidence"] = annotated_reads["seq_name"].map(top_scores)
    return annotated_reads


__all__ = ["hydrate_clusters"]
