#!/usr/bin/env python3

"""CLI entrypoint for rendering clustering plots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

import pandas as pd

from nanana.lib.cli_helpers import LOG_LEVEL_CHOICES, configure_logger
from nanana.lib.plotting import scatter_clusters


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

    if args.annotate is None:
        annotate = labels_df is not None or args.label_column in cluster_df.columns
    else:
        annotate = args.annotate

    try:
        scatter_clusters(
            cluster_df,
            output_path,
            annotate=annotate,
            labels=labels_df,
            label_column=args.label_column,
            figure_size=figure_size,
            dpi=args.dpi,
        )
    except Exception as exc:  # pragma: no cover - CLI friendly failure.
        logger.error("Plotting failed: %s", exc)
        return 1

    logger.info("Plot saved to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
