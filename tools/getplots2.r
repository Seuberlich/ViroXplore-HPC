#!/usr/bin/env Rscript
# ViroXplore-HPC RC8 FIX3: plot only raw NODE_ coverage tables.
# Existing PDF files in a reused output directory must never be parsed as TSV.
nodefiles <- list.files(path=".", pattern="^NODE_", full.names=FALSE)
nodefiles <- nodefiles[!grepl("\\.pdf$", nodefiles, ignore.case=TRUE)]
nodefiles <- nodefiles[!is.na(file.info(nodefiles)$isdir) & !file.info(nodefiles)$isdir]
created <- 0L
for (filename in nodefiles) {
    coverage <- tryCatch(read.table(filename, sep="\t", header=FALSE,
                                    quote="", comment.char="", fill=FALSE,
                                    stringsAsFactors=FALSE), error=function(e) NULL)
    if (is.null(coverage) || ncol(coverage) < 3L) {
        warning(sprintf("Skipping malformed coverage table: %s", filename))
        next
    }
    position <- suppressWarnings(as.numeric(coverage[[2L]]))
    depth <- suppressWarnings(as.numeric(coverage[[3L]]))
    good <- is.finite(position) & is.finite(depth)
    if (!any(good)) {
        warning(sprintf("Skipping coverage table without numeric positions/depths: %s", filename))
        next
    }
    output <- paste0(filename, ".pdf")
    pdf(output)
    plot(position[good], depth[good], type="l", main=filename,
         ylab="read.coverage", xlab="position", col="black")
    dev.off()
    created <- created+1L
}
if (created == 0L) stop("No valid NODE_ coverage tables to plot")
if (created != length(nodefiles)) stop(sprintf("Only plotted %d of %d NODE tables", created, length(nodefiles)))
cat(sprintf("Plotted %d NODE_ coverage tables.\n", created))