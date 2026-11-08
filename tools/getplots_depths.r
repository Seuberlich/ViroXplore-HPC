#!/usr/bin/env Rscript
# ViroXplore-HPC RC8 FIX3: select only raw .depth tables, never .depth.pdf.
# RC11 FIX3: the RefSeq mapping script passes NEW, the final filtered
# accession list. Only these exact accessions may produce coverage plots.
args <- commandArgs(trailingOnly=TRUE)
if (length(args) >= 1L) {
    if (!file.exists(args[1L])) stop("Missing accession whitelist: ", args[1L])
    accessions <- unique(trimws(readLines(args[1L], warn=FALSE)))
    accessions <- accessions[nzchar(accessions)]
    if (!length(accessions)) stop("Accession whitelist is empty")
    files <- paste0(accessions, ".depth")
    missing <- files[!file.exists(files)]
    if (length(missing)) {
        stop("Missing depth tables for filtered accessions: ", paste(missing, collapse=", "))
    }
} else {
    # Backwards compatible for standalone invocation without a whitelist.
    files <- list.files(path=".", pattern="\\.depth$", full.names=FALSE)
}
files <- files[!is.na(file.info(files)$isdir) & !file.info(files)$isdir]
created <- 0L
for (filename in files) {
    coverage <- tryCatch(read.table(filename, sep="\t", header=FALSE,
                                    quote="", comment.char="", fill=FALSE,
                                    stringsAsFactors=FALSE), error=function(e) NULL)
    if (is.null(coverage) || ncol(coverage) < 3L) {
        warning(sprintf("Skipping malformed depth table: %s", filename))
        next
    }
    position <- suppressWarnings(as.numeric(coverage[[2L]]))
    depth <- suppressWarnings(as.numeric(coverage[[3L]]))
    good <- is.finite(position) & is.finite(depth)
    if (!any(good)) {
        warning(sprintf("Skipping depth table without numeric positions/depths: %s", filename))
        next
    }
    pdf(paste0(filename, ".pdf"))
    plot(position[good], depth[good], type="l", main=filename,
         ylab="read.coverage", xlab="position", col="black")
    dev.off()
    created <- created+1L
}
if (created == 0L) stop("No valid reference depth tables to plot")
cat(sprintf("Plotted %d reference depth tables.\n", created))