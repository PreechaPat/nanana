#!/usr/bin/env python3

"""CLI entrypoint for hydrating clusters with taxonomy metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from nanana.lib.cli_helpers import LOG_LEVEL_CHOICES, configure_logger
from nanana.lib.hydrate import hydrate_clusters


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Annotate clustering results with taxonomy information."
    )
    parser.add_argument("clusters", help="Cluster TSV produced by nanana-clust.")
    parser.add_argument(
        "--dist",
        required=True,
        help="Read-to-taxonomic assignment matrix (TSV).",
    )
    parser.add_argument(
        "--output",
        default="cluster-hydrate.tsv",
        help="Output TSV containing per-read taxonomy metadata.",
    )
    parser.add_argument(
        "--cluster-summary",
        help="Optional TSV path for per-cluster taxonomy summary.",
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

    logger = configure_logger("nanana.hydrate", args.log_level)

    clusters_path = Path(args.clusters).expanduser()
    dist_path = Path(args.dist).expanduser()
    output_path = Path(args.output).expanduser()
    summary_path = Path(args.cluster_summary).expanduser() if args.cluster_summary else None

    try:
        cluster_df = pd.read_csv(clusters_path, sep="\t")
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Failed to read cluster table %s: %s", clusters_path, exc)
        return 1

    try:
        dist_df = pd.read_csv(dist_path, sep="\t", index_col=0).fillna(0)
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Failed to read distance matrix %s: %s", dist_path, exc)
        return 1

    try:
        hydrated_df, summary_df = hydrate_clusters(
            cluster_df,
            dist_df,
            sample_size=args.sample_size,
            random_state=args.random_state,
        )
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Hydration failed: %s", exc)
        return 1

    hydrated_df.to_csv(output_path, sep="\t", index=False)
    logger.info("Hydrated assignments saved to %s", output_path)

    if summary_path is not None:
        summary_df.to_csv(summary_path, sep="\t", index_label="hdbscan_id")
        logger.info("Cluster summary saved to %s", summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
