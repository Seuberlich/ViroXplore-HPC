#!/usr/bin/env python3
"""RC8 FIX3: repair FastQC option/output and robust coverage-plot input selection.

Run from the ViroXplore-HPC root, then reconfigure to refresh generated scripts
and their checksum manifest. Does not change project data, the SIF or other stages.
Python >=3.6.
"""
import pathlib
import shutil
import sys

root = pathlib.Path(__file__).resolve().parents[1]

fastqc_pe = r'''FASTQC_THREADS="${SLURM_CPUS_PER_TASK:-${SLURM_NPROCS:-1}}"
if ! fastqc --threads "$FASTQC_THREADS" --outdir "$QC_DIR" \
    "${READ_DIRECTORY}${SAMPLE_NAME}_R1.fastq.gz" \
    "${READ_DIRECTORY}${SAMPLE_NAME}_R2.fastq.gz"; then
    echo "ERROR: FastQC failed for PE sample ${SAMPLE_NAME}" >&2
    exit 1
fi
for mate in R1 R2; do
    for ext in html zip; do
        report="${QC_DIR}/${SAMPLE_NAME}_${mate}_fastqc.${ext}"
        if [[ ! -s "$report" ]]; then
            echo "ERROR: FastQC report missing: $report" >&2
            exit 1
        fi
    done
done'''

fastqc_se = r'''FASTQC_THREADS="${SLURM_CPUS_PER_TASK:-${SLURM_NPROCS:-1}}"
if ! fastqc --threads "$FASTQC_THREADS" --outdir "$QC_DIR" \
    "${READ_DIRECTORY}${SAMPLE_NAME}_R1.fastq.gz"; then
    echo "ERROR: FastQC failed for SE sample ${SAMPLE_NAME}" >&2
    exit 1
fi
for ext in html zip; do
    report="${QC_DIR}/${SAMPLE_NAME}_R1_fastqc.${ext}"
    if [[ ! -s "$report" ]]; then
        echo "ERROR: FastQC report missing: $report" >&2
        exit 1
    fi
done'''

old_fastqc = r'''fastqc "$READ_DIRECTORY""$SAMPLE_NAME"*.fastq.gz -threads $SLURM_NPROCS
mv "$READ_DIRECTORY""$SAMPLE_NAME"*.zip $QC_DIR
mv "$READ_DIRECTORY""$SAMPLE_NAME"*.html $QC_DIR'''

r_plot_node = r'''#!/usr/bin/env Rscript
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
cat(sprintf("Plotted %d NODE_ coverage tables.\n", created))'''

r_plot_depth = r'''#!/usr/bin/env Rscript
# ViroXplore-HPC RC8 FIX3: select only raw .depth tables, never .depth.pdf.
files <- list.files(path=".", pattern="\\.depth$", full.names=FALSE)
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
cat(sprintf("Plotted %d reference depth tables.\n", created))'''

old_plot_call = 'Rscript $PLOTTING_SCRIPT'
new_plot_call = '''if ! Rscript "$PLOTTING_SCRIPT"; then
    echo "ERROR: coverage plot generation failed for sample ${SAMPLE_NAME}" >&2
    exit 1
fi'''
patches = [
    (root/'templates/01_ViroXplore-HPC_v0.1_PE_qc_trim_hostrm.sh.in', old_fastqc, fastqc_pe),
    (root/'templates/01_ViroXplore-HPC_v0.1_SE_qc_trim_hostrm.sh.in', old_fastqc, fastqc_se),
    (root/'templates/04_ViroXplore-HPC_v0.1_PE_remapping.sh.in', old_plot_call, new_plot_call),
    (root/'templates/04_ViroXplore-HPC_v0.1_SE_remapping.sh.in', old_plot_call, new_plot_call),
]
for path, old, new in patches:
    content=path.read_text()
    if old in content:
        shutil.copy2(str(path),str(path)+'.FIX3_backup')
        path.write_text(content.replace(old,new,1))
        print('PATCHED:',path.relative_to(root))
    elif new in content:
        print('ALREADY PATCHED:',path.relative_to(root))
    else:
        sys.exit('ERROR: unexpected template content: '+str(path))

for relative,updated,signature in [
    ('tools/getplots2.r',r_plot_node,'nodenames <- list.files'),
    ('tools/getplots_depths.r',r_plot_depth,'nodenames <- list.files'),
]:
    path=root/relative
    original=path.read_text()
    if original == updated:
        print('ALREADY PATCHED:',relative)
    elif signature in original:
        shutil.copy2(str(path),str(path)+'.FIX3_backup')
        path.write_text(updated)
        print('PATCHED:',relative)
    else:
        sys.exit('ERROR: unexpected plotting script content: '+str(path))

print('\nFIX3 patch applied. Regenerate scripts and checksum manifest:')
print('  bash ViroXplore-HPC_config.sh')
print('  bash ViroXplore-HPC_master.sh --dry-run')
print('Note: existing results are preserved; previous FastQC reports can be generated separately.')
