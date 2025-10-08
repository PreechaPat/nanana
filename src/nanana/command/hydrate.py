#!/usr/bin/env python3

"""CLI entrypoint for hydrating clusters with taxonomy metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from nanana import __version__
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
        "--log-level",
        default="INFO",
        choices=LOG_LEVEL_CHOICES,
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"nanana-hydrate {__version__}",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = configure_logger("nanana.hydrate", args.log_level)

    clusters_path = Path(args.clusters).expanduser()
    dist_path = Path(args.dist).expanduser()
    output_path = Path(args.output).expanduser()

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
        hydrated_df = hydrate_clusters(cluster_df, dist_df)
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Hydration failed: %s", exc)
        return 1

    hydrated_df.to_csv(output_path, sep="\t", index=False)
    logger.info("Hydrated assignments saved to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
