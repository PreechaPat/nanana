"""Shared routines for the nanana clustering workflow."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Dict, Optional

import hdbscan
import pandas as pd
import umap

from nanana.lib.fasta import _opener, readfq
from nanana.lib import kmer

DEFAULT_UMAP_PARAMS: Dict[str, float] = {
    "n_neighbors": 15,
    "min_dist": 0.1,
    "n_components": 2,
}

DEFAULT_HDBSCAN_PARAMS: Dict[str, float] = {
    "min_cluster_size": 40,
    "cluster_selection_epsilon": 0.5,
}


def cluster_fastx(
    fastx_path: str,
    *,
    kmer_size: int = 5,
    umap_kwargs: Optional[Dict[str, float]] = None,
    hdbscan_kwargs: Optional[Dict[str, float]] = None,
    logger: Optional[logging.Logger] = None,
) -> pd.DataFrame:
    """Cluster sequences from a FASTA/FASTQ file and return coordinates."""

    log = logger or logging.getLogger(__name__)

    umap_config = dict(DEFAULT_UMAP_PARAMS)
    if umap_kwargs:
        umap_config.update(umap_kwargs)

    hdbscan_config = dict(DEFAULT_HDBSCAN_PARAMS)
    if hdbscan_kwargs:
        hdbscan_config.update(hdbscan_kwargs)

    with _opener(fastx_path, "r") as handle:
        generator = readfq(handle)
        log.info("Starting k-mer counting (k=%d) on %s ...", kmer_size, fastx_path)
        t0 = perf_counter()
        seq_names, lengths, count_matrix = kmer.count_sequence_kmer(kmer_size, generator)
        km_dt = perf_counter() - t0

    num_sequences = len(seq_names)
    if num_sequences == 0:
        raise ValueError(f"No sequences were read from {fastx_path}.")

    feature_count = count_matrix.shape[1]
    log.info(
        "K-mer counting finished in %.2f s (%d sequences, %d features).",
        km_dt,
        num_sequences,
        feature_count,
    )

    log.info(
        "Starting UMAP dimensionality reduction (n_neighbors=%d, min_dist=%.2f)...",
        int(umap_config["n_neighbors"]),
        float(umap_config["min_dist"]),
    )
    t_umap = perf_counter()
    reducer = umap.UMAP(**umap_config)
    embedding = reducer.fit_transform(count_matrix)
    umap_dt = perf_counter() - t_umap
    log.info(
        "UMAP finished in %.2f s (n_samples=%d, n_components=%d).",
        umap_dt,
        embedding.shape[0],
        embedding.shape[1],
    )

    log.info(
        "Starting HDBSCAN clustering (min_cluster_size=%d, cluster_selection_epsilon=%.2f)...",
        int(hdbscan_config["min_cluster_size"]),
        float(hdbscan_config["cluster_selection_epsilon"]),
    )
    t_hdb = perf_counter()
    clusterer = hdbscan.HDBSCAN(**hdbscan_config)
    labels = clusterer.fit_predict(embedding)
    hdb_dt = perf_counter() - t_hdb
    log.info("HDBSCAN finished in %.2f s.", hdb_dt)

    metadata = pd.DataFrame(
        {
            "seq_name": seq_names,
            "length": lengths,
            "hdbscan_id": labels,
        }
    )
    coordinates = pd.DataFrame(embedding, columns=["D1", "D2"])

    return pd.concat([metadata, coordinates], axis=1)


__all__ = ["cluster_fastx", "DEFAULT_HDBSCAN_PARAMS", "DEFAULT_UMAP_PARAMS"]
