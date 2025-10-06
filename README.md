# Nanana

## CLI workflow

- `nanana-clust <reads.fastx>` builds UMAP/HDBSCAN clusters and stores the coordinates as TSV.
- `nanana-hydrate <clusters.tsv> --dist <read_taxon.tsv>` enriches the cluster table with per-read taxonomy.
- `nanana-plot <clusters.tsv>` renders a scatter plot of the embedding, optionally annotating clusters when taxonomy is present.
