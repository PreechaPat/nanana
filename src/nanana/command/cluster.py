#!/usr/bin/env python3

"""CLI entrypoint for the clustering phase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nanana import __version__
from nanana.lib.cli_helpers import LOG_LEVEL_CHOICES, configure_logger
from nanana.lib.cluster_pipeline import cluster_fastx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cluster reads based on k-mer content and write coordinates to TSV."
    )
    parser.add_argument("fastx", help="Input FASTA/FASTQ file.")
    parser.add_argument(
        "--output",
        default="cluster.tsv",
        help="Output clustering table (TSV).",
    )
    parser.add_argument(
        "--kmer-size",
        type=int,
        default=5,
        help="k-mer size for counting (default: 5).",
    )
    parser.add_argument(
        "--n-neighbors",
        type=int,
        default=15,
        help="UMAP number of neighbours (default: 15).",
    )
    parser.add_argument(
        "--min-dist",
        type=float,
        default=0.1,
        help="UMAP minimum distance (default: 0.1).",
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=40,
        help="HDBSCAN minimum cluster size (default: 40).",
    )
    parser.add_argument(
        "--cluster-epsilon",
        type=float,
        default=0.5,
        help="HDBSCAN cluster selection epsilon (default: 0.5).",
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
        version=f"nanana-cluster {__version__}",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger = configure_logger("nanana.cluster", args.log_level)
    output_path = Path(args.output).expanduser()

    try:
        cluster_df = cluster_fastx(
            args.fastx,
            kmer_size=args.kmer_size,
            umap_kwargs={
                "n_neighbors": args.n_neighbors,
                "min_dist": args.min_dist,
                "n_components": 2,
            },
            hdbscan_kwargs={
                "min_cluster_size": args.min_cluster_size,
                "cluster_selection_epsilon": args.cluster_epsilon,
            },
            logger=logger,
        )
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Clustering failed: %s", exc)
        return 1

    cluster_df.to_csv(output_path, sep="\t", index=False)
    logger.info("Cluster assignments saved to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
