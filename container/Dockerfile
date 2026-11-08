# ViroXplore-HPC v1.0.0 build recipe; test each new image independently.
FROM mambaorg/micromamba:2.10.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/viroxplore-environment.yml
RUN micromamba install -y -n base -f /tmp/viroxplore-environment.yml && \
    micromamba clean --all --yes

# Running via `apptainer exec` does not execute the Docker ENTRYPOINT.
ENV PATH=/opt/conda/bin:$PATH
COPY --chown=$MAMBA_USER:$MAMBA_USER module_compat.sh /opt/viroxplore/module_compat.sh
COPY --chown=$MAMBA_USER:$MAMBA_USER smoke_test.sh /opt/viroxplore/smoke_test.sh

LABEL org.opencontainers.image.title="ViroXplore-HPC runtime" \
      org.opencontainers.image.description="Bioinformatics dependencies for ViroXplore-HPC v1.0.0"
