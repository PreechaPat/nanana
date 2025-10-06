"""Plotting helpers for nanana cluster visualisations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd


def scatter_clusters(
    cluster_df: pd.DataFrame,
    output_path: str | Path,
    *,
    annotate: bool = False,
    labels: Optional[pd.DataFrame] = None,
    label_column: str = "name",
    figure_size: Tuple[float, float] = (20.0, 20.0),
    dpi: int = 300,
) -> None:
    """Create a 2D scatter plot of cluster embeddings."""

    required_columns = {"D1", "D2", "hdbscan_id"}
    missing_columns = required_columns.difference(cluster_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Cluster table missing required columns: {missing}.")

    plt.ioff()
    fig, ax = plt.subplots(figsize=figure_size)
    ax.scatter(
        cluster_df["D1"],
        cluster_df["D2"],
        c=cluster_df["hdbscan_id"],
        cmap="nipy_spectral",
        s=3,
    )
    ax.grid(True)
    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    ax.set_aspect("equal", "datalim")

    if annotate:
        label_df: Optional[pd.DataFrame]
        if labels is not None:
            if "hdbscan_id" not in labels.columns:
                raise ValueError("Label table must include 'hdbscan_id'.")
            if label_column not in labels.columns:
                raise ValueError(f"Label table must include '{label_column}'.")
            label_df = labels.set_index("hdbscan_id")[[label_column]]
        else:
            if label_column not in cluster_df.columns:
                raise ValueError(
                    f"Column '{label_column}' not present; provide --labels or disable annotation."
                )
            label_df = (
                cluster_df.dropna(subset=[label_column])
                .drop_duplicates(subset=["hdbscan_id"])
                .set_index("hdbscan_id")[[label_column]]
            )

        centers = cluster_df.groupby("hdbscan_id")[["D1", "D2"]].mean()
        annotated = centers.join(label_df, how="inner")

        for cluster_id, row in annotated.iterrows():
            if pd.isna(row[label_column]):
                continue
            annotation = f"{cluster_id}:{row[label_column]}"
            ax.annotate(annotation, (row["D1"], row["D2"]), weight="bold", size=14)

    output_path = Path(output_path)
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)


__all__ = ["scatter_clusters"]
