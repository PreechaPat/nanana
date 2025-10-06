import subprocess
import shutil
import pandas as pd
import os

def run_skani_triangle(input_fasta, output_file="skani_triangle.tsv"):
    """
    Runs `skani triangle` on a single multi-sequence FASTA file using `-i` option.

    Parameters:
        input_fasta (str): Path to a FASTA file with multiple sequences/genomes.
        output_file (str): File to save skani triangle result.

    Returns:
        pd.DataFrame: Distance matrix as a pandas DataFrame.
    """
    if not shutil.which("skani"):
        raise OSError("`skani` executable not found in PATH.")

    if not os.path.exists(input_fasta):
        raise FileNotFoundError(f"Input file not found: {input_fasta}")

    cmd = ["skani", "triangle", "-i", input_fasta, "-o", output_file]

    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Skani triangle failed: {e}")

    # Read and return the result
    df = pd.read_csv(output_file, sep="\t", index_col=0)
    
    return df

# Example usage
if __name__ == "__main__":
    input_file = "example_multi_genomes.fasta"  # Change to your actual input
    run_skani_triangle_with_i(input_file, "triangle_output.tsv")