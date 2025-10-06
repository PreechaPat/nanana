"""Utilities for enriching cluster assignments with taxonomy metadata."""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from nanana.lib.taxon import name as fetch_taxon_name


def _sample_group(sample_size: int, random_state: Optional[int]) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def sampler(group: pd.DataFrame) -> pd.DataFrame:
        target = 1 if len(group) < sample_size else sample_size
        return group.sample(n=target, random_state=random_state)

    return sampler


def build_cluster_summary(
    cluster_df: pd.DataFrame,
    read_taxon_df: pd.DataFrame,
    *,
    sample_size: int = 5,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    """Return per-cluster taxonomy assignments."""

    required_columns = {"hdbscan_id", "seq_name"}
    missing_columns = required_columns.difference(cluster_df.columns)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"Cluster table is missing required columns: {columns}.")

    sampled_reads = (
        cluster_df.groupby("hdbscan_id", group_keys=False)
        .apply(_sample_group(sample_size, random_state))
    )

    if sampled_reads.empty:
        raise ValueError("No reads available to assign taxonomy.")

    group_taxids: dict[int, str] = {}

    for cluster_id, group in sampled_reads.groupby("hdbscan_id"):
        read_ids = group["seq_name"].values
        dist_slice = read_taxon_df.reindex(read_ids).dropna(how="all")
        if dist_slice.empty:
            continue
        top_taxid = dist_slice.sum(axis=0).idxmax()
        group_taxids[int(cluster_id)] = str(top_taxid)

    if not group_taxids:
        raise ValueError("Unable to assign taxonomy to any cluster with provided distances.")

    summary_df = (
        pd.DataFrame(
            {
                "hdbscan_id": list(group_taxids.keys()),
                "TaxID": list(group_taxids.values()),
            }
        )
        .set_index("hdbscan_id")
        .sort_index()
    )

    taxid_list = summary_df["TaxID"].tolist()
    taxname_df = fetch_taxon_name(ids=taxid_list)
    taxname_df["TaxID"] = taxname_df["TaxID"].astype(str)
    id_to_name = dict(zip(taxname_df["TaxID"], taxname_df["Name"]))
    summary_df["name"] = summary_df["TaxID"].map(id_to_name)

    return summary_df


def hydrate_clusters(
    cluster_df: pd.DataFrame,
    read_taxon_df: pd.DataFrame,
    *,
    sample_size: int = 5,
    random_state: Optional[int] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach cluster-level taxonomy metadata to each read."""

    summary_df = build_cluster_summary(
        cluster_df,
        read_taxon_df,
        sample_size=sample_size,
        random_state=random_state,
    )
    annotated_reads = cluster_df.merge(
        summary_df.reset_index(),
        on="hdbscan_id",
        how="left",
    )
    return annotated_reads, summary_df


__all__ = ["build_cluster_summary", "hydrate_clusters"]
