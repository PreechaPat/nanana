from itertools import product
import numpy as np
import numpy.typing as npt

base_for = "ACGT"
base_rev = "TGCA"
comp_tab = str.maketrans(base_for, base_rev)

# original implementation of heng li
# def count_kmer(h, k, seq):
# 	l = len(seq)
# 	if l < k: return
# 	for i in range(l - k + 1):
# 		kmer_for = seq[i:(i+k)]
# 		if 'N' in kmer_for: continue
# 		kmer_rev = kmer_for.translate(comp_tab)[::-1]
# 		if kmer_for < kmer_rev: kmer = kmer_for
# 		else: kmer = kmer_rev
# 		if kmer in h:
# 			h[kmer] += 1
# 		else: h[kmer] = 1

def count_kmer(h: npt.NDArray, hsh_fn, k_size, seq):
	# Modified from Mr. Hli. Now retrieve hsh_fn(for location) + numpy
	seq_size = len(seq)
	if seq_size < k_size: return
	for i in range(seq_size - k_size + 1):
		kmer_for = seq[i:(i+k_size)]
		kmer_rev = kmer_for.translate(comp_tab)[::-1]
		if kmer_for < kmer_rev: 
			kmer = kmer_for
		else: 
			kmer = kmer_rev
		if kmer in hsh_fn:
			h[hsh_fn[kmer]] += 1

def make_kmer_list(k_size):
    # Build all permute k-mer without duplication
    kmers = [''.join(x) for x in product("ACGT", repeat=k_size)]
    combined = set()
    for kmer_for in kmers:
        # Find cannonical k-mer
        kmer_rev = kmer_for.translate(comp_tab)[::-1]
        if kmer_for < kmer_rev:
              kmer = kmer_for
        else:
              kmer = kmer_rev
        combined.add(kmer)
    combined = list(combined)
    combined.sort()
    return combined

def count_sequence_kmer(k_size, generator):
      # Arguments:
      # ksize = k-mer size
      # generator = return name, sequence, and quality (maybe not using it)
      # Do:
      # Calculate
      # Create hash lookup for putting thing in numpy array
      hsh_fn = dict()
      for i, kmer in enumerate(make_kmer_list(k_size)):
            hsh_fn[kmer] = i
            
      array_size = len(hsh_fn)

      seq_names = []
      lengths = []
      counts = []
      for record in generator:
            name, seq, qual = record
            init_np = np.zeros(array_size, np.uint16)
            count_kmer(init_np, hsh_fn, k_size, seq)
            # Append result
            seq_names.append(name)
            lengths.append(len(seq))
            counts.append(init_np)

      return (seq_names, lengths, np.vstack(counts))
