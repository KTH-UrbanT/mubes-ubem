FROM nrel/energyplus:9.5.0 AS energyplus

FROM python:3.9-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential libgfortran5 libgomp1 libstdc++6 libx11-6 libtk8.6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=energyplus /usr/local/EnergyPlus-9-5-0 /usr/local/EnergyPlus-9-5-0
RUN ln -s /usr/local/EnergyPlus-9-5-0/energyplus /usr/local/bin/energyplus

WORKDIR /project
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PATH="/usr/local/EnergyPlus-9-5-0:${PATH}"
WORKDIR /project/bin
