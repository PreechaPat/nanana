#!/usr/bin/env python3

import argparse
import gzip
import logging
import os
import shutil
import subprocess
import sys

import pandas as pd
import pysam

from nanana import __version__

# Global Logger Setup
def setup_logger(log_file: str):
    logger = logging.getLogger("polish_logger")
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels of logs

    # Console handler for INFO level and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(console_handler)

    # File handler for DEBUG level and above
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)

    return logger

log_file = "polish.log"  # Default log file
logger = setup_logger(log_file)

def run_command(command, log_file: str):
    logger.debug(f"Running: {command}")
    try:
        with open(log_file, "a") as log_file:
            subprocess.run(command, shell=True, check=True, stdout=log_file, stderr=log_file)
            logger.debug(f"Success: {command}")
    except subprocess.CalledProcessError:
        logger.error(f"Failed: {command}")
        raise

def read_correction(fq: str, out_dir:str):
    logger.debug(f"Correcting reads from {fq} into {out_dir}")
    logfile = os.path.join(out_dir, "canu.log")
    run_command(
        f"canu -correct -p corrected_reads -d {out_dir} -nanopore-raw {fq} "
        f"genomeSize=1000 stopOnLowCoverage=1 minInputCoverage=2 minReadLength=400 minOverlapLength=200",
        logfile
    )
    corrected = os.path.join(out_dir, "corrected_reads.correctedReads.fasta")
    if not os.path.exists(corrected):
        gz = corrected + ".gz"
        if os.path.exists(gz):
            with gzip.open(gz, "rb") as f_in, open(corrected, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            raise FileNotFoundError("Corrected reads not found")
    return corrected

def run_skani_and_select_best(corrected_reads, out_dir):
    """
    Runs skani on the corrected reads and selects the best read based on ANI values.

    Args:
        corrected_reads (str): Path to the corrected reads file.
        out_dir (str): Directory to store skani output.

    Returns:
        str: The ID of the best read for the cluster representative.
    """
    # Define output paths
    skani_output = os.path.join(out_dir, "skani_output.tsv")
    log_file = os.path.join(out_dir, "skani_run.log")

    # Run skani
    run_command(
        f"skani dist --qi -q {corrected_reads} --ri -r {corrected_reads} -o {skani_output} -t 48",
        log_file
    )

    # Parse skani output and select the best read
    df = pd.read_csv(skani_output, sep="\t")
    df = df[df["Ref_name"] != df["Query_name"]].copy()
    df["pair"] = df.apply(lambda row: tuple(sorted([row["Ref_name"], row["Query_name"]])), axis=1)
    df = df.drop_duplicates(subset="pair")
    df["ANI"] = pd.to_numeric(df["ANI"], errors="coerce")
    best_ref = df.groupby("Ref_name")["ANI"].mean().idxmax()

    logger.info(f"Best read for cluster representative ID: {best_ref}")
    return best_ref

def prepare_draft_fasta(draft_id, corrected_reads, out_path):

    log_file = os.path.join(os.path.dirname(out_path), "draft_extraction.log")
    if "id=" in draft_id:
        fasta_id = draft_id.split("id=")[-1].strip()
    else:
        raise ValueError("Invalid draft ID format")
    run_command(
        f"awk '/^>.*id={fasta_id}/{{print_flag=1; print; next}} /^>/{{print_flag=0}} print_flag' {corrected_reads} > {out_path}",
        log_file
    )
    if os.path.getsize(out_path) == 0:
        raise RuntimeError("Draft read extraction failed")
    return out_path

def align_reads(draft_fasta, corrected_reads, sam_out):

    log_file = os.path.join(os.path.dirname(sam_out), "alignment.log")
    run_command(
        f"minimap2 -ax map-ont --no-long-join -r100 -a {draft_fasta} {corrected_reads} -o {sam_out}",
        log_file
    )
    return sam_out

def polish_with_racon(corrected_reads, sam_file, draft_fasta, output_fasta):
    log_file = os.path.join(os.path.dirname(output_fasta), "racon_polish.log")
    try:
        run_command(
            f"racon --quality-threshold=9 -w 250 {corrected_reads} {sam_file} {draft_fasta} > {output_fasta}",
            log_file
        )
    except subprocess.CalledProcessError:
        logger.warning("Racon failed — using unpolished draft")
        run_command(f"cp {draft_fasta} {output_fasta}", log_file)

def polish_cluster(cluster_dir: str, input_fastq: str):

    tmp_dir = os.path.join(cluster_dir, "tmp")
    consensus_dir = os.path.join(cluster_dir, "consensus")
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(consensus_dir, exist_ok=True)

    corrected = read_correction(input_fastq, tmp_dir)
    draft_id = run_skani_and_select_best(corrected, tmp_dir)
    draft_fasta = prepare_draft_fasta(draft_id, corrected, os.path.join(consensus_dir, "draft_read.fasta"))
    sam_file = align_reads(draft_fasta, corrected, os.path.join(tmp_dir,"aligned.sam"))
    polish_with_racon(corrected, sam_file, draft_fasta, os.path.join(consensus_dir, "racon_consensus.fasta"))

    logger.info(f"Finished polishing {cluster_dir}")

def _write_cluster_fastq(records: dict[str, dict[str, str]], output_path: str) -> str:
    with open(output_path, "w") as handle:
        for name, data in records.items():
            handle.write(f"@{name}\n{data['sequence']}\n+\n{data['quality']}\n")
    return output_path

def extract_sequences(fastq_path, tsv_path, output_dir, cluster_id=None):
    """
    Extract sequences for the requested clusters into per-cluster FASTQ files.
    """
    df = pd.read_csv(tsv_path, sep="\t")
    if cluster_id is not None:
        cluster_ids = [int(cluster_id)]
    else:
        cluster_ids = sorted({int(cid) for cid in df['hdbscan_id'].dropna().unique()})
    logger.info(f"Processing {len(cluster_ids)} cluster(s): {cluster_ids}")

    fastq_records = {}
    with pysam.FastxFile(fastq_path) as fq:
        for entry in fq:
            fastq_records[entry.name] = {"sequence": entry.sequence, "quality": entry.quality}

    extracted_clusters: dict[int, dict[str, str]] = {}
    for cid in cluster_ids:
        cluster_dir = os.path.join(output_dir, f"cluster_{cid}")
        os.makedirs(cluster_dir, exist_ok=True)

        sub_df = df[df['hdbscan_id'] == cid]
        target_names = set(sub_df["seq_name"])
        cluster_seqs = {name: fastq_records[name] for name in target_names if name in fastq_records}

        if not cluster_seqs:
            logger.warning(f"No sequences found for cluster {cid}")
            continue

        cluster_fastq_path = os.path.join(cluster_dir, "cluster_reads.fastq")
        _write_cluster_fastq(cluster_seqs, cluster_fastq_path)
        logger.info(f"Wrote {len(cluster_seqs)} sequences to {cluster_fastq_path}")
        extracted_clusters[cid] = {
            "cluster_dir": cluster_dir,
            "fastq_path": cluster_fastq_path,
        }

    return extracted_clusters

def polish_extracted_clusters(extracted_clusters: dict[int, dict[str, str]]):
    """
    Polish each cluster using the previously extracted FASTQ files.
    """
    for cid, metadata in extracted_clusters.items():
        logger.info(f"Polishing cluster {cid}")
        polish_cluster(metadata["cluster_dir"], metadata["fastq_path"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract and polish cluster reads."
    )
    parser.add_argument(
        "fastx",
        help="Input FASTA/FASTQ file.",
    )
    parser.add_argument(
        "--tsv",
        required=True,
        help="Cluster assignment file (TSV).",
    )
    parser.add_argument(
        "-c",
        "--cluster",
        type=str,
        help="Optional cluster ID to process.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"nanana-polish {__version__}",
    )
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    tsv_file = args.tsv
    fastx_file = args.fastx
    output_root = "cluster_outputs"
    os.makedirs(output_root, exist_ok=True)

    extracted_clusters = extract_sequences(fastx_file, tsv_file, output_root, args.cluster)
    polish_extracted_clusters(extracted_clusters)

    return 0

if __name__ == "__main__":
    sys.exit(main())
