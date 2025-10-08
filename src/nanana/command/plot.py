#!/usr/bin/env python3

"""CLI entrypoint for rendering clustering plots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple

import pandas as pd

from nanana.lib.cli_helpers import LOG_LEVEL_CHOICES, configure_logger
from nanana.lib.plotting import scatter_clusters
from nanana.lib.taxon import name as fetch_taxon_name


def _sample_group(sample_size: int, random_state: Optional[int]) -> Callable[[pd.DataFrame], pd.DataFrame]:
    def sampler(group: pd.DataFrame) -> pd.DataFrame:
        target = 1 if len(group) < sample_size else sample_size
        return group.sample(n=target, random_state=random_state)

    return sampler


def _build_cluster_summary(
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a 2D plot from nanana clustering coordinates."
    )
    parser.add_argument(
        "clusters",
        help="Cluster TSV produced by nanana-clust or nanana-hydrate.",
    )
    parser.add_argument(
        "--labels",
        help="Optional TSV with per-cluster annotations (hdbscan_id column required).",
    )
    parser.add_argument(
        "--png",
        default="umap_hdbscan_plot.png",
        help="Output PNG filename (default: umap_hdbscan_plot.png).",
    )
    parser.add_argument(
        "--figure-size",
        type=float,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(20.0, 20.0),
        help="Figure size in inches (default: 20 20).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution of the saved plot (default: 300).",
    )
    parser.add_argument(
        "--label-column",
        default="name",
        help="Column used for plot annotations (default: name).",
    )
    parser.add_argument(
        "--annotate",
        dest="annotate",
        action="store_true",
        help="Force annotation even if labels are not detected automatically.",
    )
    parser.add_argument(
        "--no-annotate",
        dest="annotate",
        action="store_false",
        help="Disable annotations even if labels are available.",
    )
    parser.set_defaults(annotate=None)
    parser.add_argument(
        "--confidence-column",
        help="Per-read confidence column; low values use --low-confidence-marker. "
        "Defaults to 'confidence' when present.",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.0,
        help="Scores at or below this value render with the low-confidence marker (default: 0.0).",
    )
    parser.add_argument(
        "--low-confidence-marker",
        default="x",
        help="Marker used for reads at or below the confidence threshold (default: x).",
    )
    parser.add_argument(
        "--high-confidence-marker",
        default="o",
        help="Marker used for reads above the confidence threshold (default: o).",
    )
    parser.add_argument(
        "--dist",
        help="Optional read-to-taxonomic assignment matrix (TSV) for deriving cluster summaries.",
    )
    parser.add_argument(
        "--cluster-summary",
        help="Optional TSV path for saving per-cluster taxonomy summary.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of reads to sample per cluster during voting (default: 5).",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        help="Random seed applied to sampling for reproducibility.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=LOG_LEVEL_CHOICES,
        help="Logging verbosity (default: INFO).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = configure_logger("nanana.plot", args.log_level)

    clusters_path = Path(args.clusters).expanduser()
    labels_path = Path(args.labels).expanduser() if args.labels else None
    dist_path = Path(args.dist).expanduser() if args.dist else None
    summary_path = Path(args.cluster_summary).expanduser() if args.cluster_summary else None
    output_path = Path(args.png).expanduser()
    width, height = args.figure_size
    figure_size: Tuple[float, float] = (float(width), float(height))

    try:
        cluster_df = pd.read_csv(clusters_path, sep="\t")
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Failed to read cluster table %s: %s", clusters_path, exc)
        return 1

    labels_df = None
    if labels_path is not None:
        try:
            labels_df = pd.read_csv(labels_path, sep="\t")
        except Exception as exc:  # pragma: no cover - CLI friendly failure.
            logger.error("Failed to read label table %s: %s", labels_path, exc)
            return 1

    summary_df = None
    if dist_path is not None:
        try:
            dist_df = pd.read_csv(dist_path, sep="\t", index_col=0).fillna(0)
        except Exception as exc:  # pragma: no cover - CLI friendly failure.
            logger.error("Failed to read distance matrix %s: %s", dist_path, exc)
            return 1

        try:
            summary_df = _build_cluster_summary(
                cluster_df,
                dist_df,
                sample_size=args.sample_size,
                random_state=args.random_state,
            )
        except Exception as exc:  # pragma: no cover - CLI friendly failure.
            logger.error("Failed to build cluster summary: %s", exc)
            return 1

        if labels_df is None:
            labels_df = summary_df.reset_index()

        if summary_path is not None:
            summary_df.to_csv(summary_path, sep="\t", index_label="hdbscan_id")
            logger.info("Cluster summary saved to %s", summary_path)
    elif summary_path is not None:
        logger.error("--cluster-summary requires --dist")
        return 1

    if args.annotate is None:
        annotate = labels_df is not None or args.label_column in cluster_df.columns
    else:
        annotate = args.annotate

    confidence_column = args.confidence_column
    if confidence_column is None and "confidence" in cluster_df.columns:
        confidence_column = "confidence"
    elif confidence_column and confidence_column not in cluster_df.columns:
        logger.warning(
            "Confidence column %s not found in cluster table; disabling confidence markers.",
            confidence_column,
        )
        confidence_column = None

    try:
        scatter_clusters(
            cluster_df,
            output_path,
            annotate=annotate,
            labels=labels_df,
            label_column=args.label_column,
            figure_size=figure_size,
            dpi=args.dpi,
            confidence_column=confidence_column,
            confidence_threshold=args.confidence_threshold,
            low_confidence_marker=args.low_confidence_marker,
            high_confidence_marker=args.high_confidence_marker,
        )
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Plotting failed: %s", exc)
        return 1

    logger.info("Plot saved to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
