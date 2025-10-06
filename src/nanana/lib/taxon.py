import sys
import shutil
import pandas as pd
from io import StringIO
from subprocess import Popen, PIPE
from warnings import warn

def log(*args, level="debug"):
    """Print log messages with a standard prefix."""
    print(f"[pytaxonkit::{level}]", *args, file=sys.stderr)

def _check_taxonkit():
    """Ensure taxonkit is installed and in PATH."""
    if shutil.which("taxonkit") is None:
        sys.exit("Error: 'taxonkit' is not installed or not in your PATH.\n"
                 "Please install it: https://github.com/shenwei356/taxonkit")

def name(ids, data_dir=None, debug=False):
    """
    Retrieve taxon names using 'taxonkit lineage --show-name --no-lineage'.

    Parameters
    ----------
    ids : list or iterable
        A list of taxids (ints or strings are ok).
    data_dir : str, optional
        Location of NCBI taxonomy `.dmp` files. Default is ~/.taxonkit/.
    debug : bool, optional
        If True, print debug messages including system calls.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: TaxID and Name.
    """
    _check_taxonkit()

    idlist = "\n".join(map(str, ids)) + "\n"
    if idlist == "\n":
        warn("No input for pytaxonkit.name", UserWarning)
        return pd.DataFrame(columns=["TaxID", "Name"])

    arglist = ["taxonkit", "lineage", "--show-name", "--no-lineage"]
    # if data_dir:
    #     arglist.extend(["--data-dir", data_dir])  # Ensure `data_dir` is validated externally.

    if debug:
        log("Running command:", " ".join(arglist), level="info")

    proc = Popen(arglist, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    out, err = proc.communicate(input=idlist)

    if proc.returncode != 0:
        raise RuntimeError(f"taxonkit failed with error:\n{err.strip()}")

    data = pd.read_csv(StringIO(out), sep="\t", header=None, names=["TaxID", "Name"])
    return data