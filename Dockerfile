FROM ghcr.io/prefix-dev/pixi:0.48.1 AS build

# copy source code, pixi.toml and pixi.lock to the container
COPY . /nanana
WORKDIR /nanana
# run some compilation / build task (if needed)
# RUN pixi run build
# run the `install` command (or any other). This will also install the dependencies into `/app/.pixi`
# assumes that you have a `prod` environment defined in your pixi.toml
RUN pixi install -e prod
# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e prod > /shell-hook.sh

RUN echo 'export NUMBA_CACHE_DIR="/tmp/nanana-numba-cache"' >> /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM python:3.12-slim-bookworm AS production

# Add ps, since nextflow need it...
RUN apt-get update \
 && apt-get install -y --no-install-recommends procps


# Add path
ENV NUMBA_CACHE_DIR="/tmp/nanana-numba-cache"
ENV PATH="/nanana/.pixi/envs/prod/bin:${PATH}"

# only copy the production environment into prod container
# please note that the "prefix" (path) needs to stay the same as in the build container
COPY --from=build /nanana/.pixi/envs/prod /nanana/.pixi/envs/prod
COPY --from=build /nanana/src /nanana/src
COPY --from=build /shell-hook.sh /shell-hook.sh
WORKDIR /nanana
# EXPOSE 8000

# Final cleanup
RUN apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/*


# set the entrypoint to the shell-hook script (activate the environment and run the command)
# no more pixi needed in the prod container
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]

# CMD ["start-server"]
