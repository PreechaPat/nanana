import os
import subprocess
import sys

def check_docker():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        sys.exit("Docker is not installed or not running. Please install/start Docker.")

def run_command(command):
    subprocess.run(command, shell=True, check=True)

def main(fq):
    check_docker()
    
    bname = os.path.splitext(os.path.basename(fq))[0]
    os.makedirs(f"{bname}/tmp", exist_ok=True)
    TMP = f"{bname}/tmp"
    
    # Run Canu for correction
    canu_cmd = (
        f"docker run -u $(id -u):$(id -g) -v $PWD:$PWD -w $PWD --rm "
        f"quay.io/biocontainers/canu:2.2--ha47f30e_0 canu -correct -p corrected_reads "
        f"-d {bname} -nanopore-raw {fq} genomeSize=1000 stopOnLowCoverage=1 "
        f"minInputCoverage=2 minReadLength=400 minOverlapLength=200"
    )
    run_command(canu_cmd)
    
    # Unzip corrected reads
    run_command(f"gunzip {bname}/corrected_reads.correctedReads.fasta.gz")
    corrected_reads = f"{bname}/corrected_reads.correctedReads.fasta"
    
    # Split reads
    SPLIT_DIR = f"{TMP}/split_reads"
    os.makedirs(SPLIT_DIR, exist_ok=True)
    run_command(f"split -l 2 {corrected_reads} {SPLIT_DIR}/split_reads")
    run_command(f"find {SPLIT_DIR}/split_reads* > {SPLIT_DIR}/read_list.txt")
    
    # Run FastANI
    fastani_cmd = (
        f"docker run -u $(id -u):$(id -g) -v $PWD:$PWD -w $PWD --rm "
        f"quay.io/biocontainers/fastani:1.34--h4dfc31f_0 fastANI "
        f"--ql {SPLIT_DIR}/read_list.txt --rl {SPLIT_DIR}/read_list.txt "
        f"-o {SPLIT_DIR}/fastani_output.ani -t 48 -k 16 --fragLen 160"
    )
    run_command(fastani_cmd)
    
    # Determine draft read
    draft_read = subprocess.getoutput(
        f"awk 'NR>1{{name[$1] = $1; arr[$1] += $3; count[$1] += 1}}  "
        f"END{{for (a in arr) {{print arr[a] / count[a], name[a] }}}}' "
        f"{SPLIT_DIR}/fastani_output.ani | sort -rg | cut -d ' ' -f2 | head -n1"
    ).strip()
    
    # Create consensus directory
    CONS_DIR = f"{bname}/consensus"
    os.makedirs(CONS_DIR, exist_ok=True)
    draft_read_fasta = f"{CONS_DIR}/draft_read.fasta"
    run_command(f"cat {draft_read} > {draft_read_fasta}")
    
    # Run Minimap2
    minimap2_cmd = (
        f"docker run -u $(id -u):$(id -g) -v $PWD:$PWD -w $PWD --rm "
        f"quay.io/biocontainers/minimap2:2.26--he4a0461_2 minimap2 "
        f"-ax map-ont --no-long-join -r100 -a {draft_read_fasta} {corrected_reads} "
        f"-o {TMP}/aligned.sam"
    )
    run_command(minimap2_cmd)
    
    # Run Racon
    racon_output = f"{CONS_DIR}/racon_consensus.fasta"
    racon_cmd = (
        f"docker run -u $(id -u):$(id -g) -v $PWD:$PWD -w $PWD --rm "
        f"quay.io/biocontainers/racon:1.5.0--h21ec9f0_2 racon "
        f"--quality-threshold=9 -w 250 {corrected_reads} {TMP}/aligned.sam {draft_read_fasta} "
        f"> {racon_output}"
    )
    try:
        run_command(racon_cmd)
    except subprocess.CalledProcessError:
        run_command(f"cat {draft_read_fasta} > {racon_output}")
    
    # Run Medaka
    medaka_output = f"{CONS_DIR}/consensus_medaka"
    medaka_cmd = (
        f"docker run -u $(id -u):$(id -g) -v $PWD:$PWD -w $PWD --rm "
        f"ontresearch/medaka:latest medaka_consensus "
        f"-i {corrected_reads} -d {racon_output} -o {medaka_output} -t 4 -m r941_min_sup_g507"
    )
    try:
        run_command(medaka_cmd)
        run_command(f"cat {medaka_output}/consensus.fasta > {CONS_DIR}/{bname}.consensus_medaka.fasta")
    except subprocess.CalledProcessError:
        run_command(f"cat {racon_output} > {CONS_DIR}/{bname}.consensus_medaka.fasta")
    print("Pipeline completed successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input.fastq>")
        sys.exit(1)
    main(sys.argv[1])
