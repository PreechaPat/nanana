# Source: https://github.com/lh3/readfq/
# TODO: Well, I can pythonify it.

import io
import sys
import gzip

def _opener(filename, mode, encoding='utf8'):
    if filename == '-':
        sys.stderr.write("Reading from stdin\n")
        #return open(sys.stdin.buff, mode, encoding=encoding)
        return io.TextIOWrapper(sys.stdin.buffer, encoding=encoding)
    elif filename.endswith('.gz'):
        return gzip.open(filename, mode + 't', encoding=encoding)
    else:
        return open(filename, mode, encoding=encoding)

def readfq(fp, description = False): # this is a generator function
    last = None # this is a buffer keeping the last unprocessed line
    while True: # mimic closure; is it a bad idea?
        if not last: # the first record or a record following a fastq
            for l in fp: # search for the start of the next record
                if l[0] in '>@': # fasta/q header line
                    last = l[:-1] # save this line
                    break
        if not last: break
        # Last is the fasta header (whole)
        name, _, description = last[1:].partition(" ")
        seqs = []
        last = None
        # name = last[1:].partition(" ")[0]
        # name, seqs, last = last[1:].partition(" ")[0], [], None
        for l in fp: # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+': # this is a fasta record
            yield name, ''.join(seqs), None # yield a fasta record
            if not last: break
        else: # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp: # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq): # have read enough quality
                    last = None
                    yield name, seq, ''.join(seqs); # yield a fastq record
                    break
            if last: # reach EOF before reading enough quality
                yield name, seq, None # yield a fasta record instead
                break