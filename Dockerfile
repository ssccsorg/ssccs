FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# System packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    device-tree-compiler \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Rust installation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# RISC-V targets for Rust cross-compilation
RUN rustup target add riscv64imac-unknown-none-elf

# Pre-built RISC-V GCC toolchain for bare-metal (riscv64-unknown-elf)
RUN wget https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/2026.05.19/riscv64-elf-ubuntu-24.04-gcc.tar.xz \
    && tar -xJf riscv64-elf-ubuntu-24.04-gcc.tar.xz -C /opt \
    && rm riscv64-elf-ubuntu-24.04-gcc.tar.xz \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-gcc /usr/local/bin/riscv64-unknown-elf-gcc \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-g++ /usr/local/bin/riscv64-unknown-elf-g++ \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-ar /usr/local/bin/riscv64-unknown-elf-ar \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-as /usr/local/bin/riscv64-unknown-elf-as \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-ld /usr/local/bin/riscv64-unknown-elf-ld \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-objdump /usr/local/bin/riscv64-unknown-elf-objdump \
    && ln -sf /opt/riscv/bin/riscv64-unknown-elf-objcopy /usr/local/bin/riscv64-unknown-elf-objcopy
ENV PATH="/opt/riscv/bin:${PATH}"

# Spike + pk from source
RUN git clone https://github.com/riscv-software-src/riscv-isa-sim.git /tmp/spike \
    && cd /tmp/spike && mkdir build && cd build \
    && ../configure --prefix=/usr/local && make -j$(nproc) && make install \
    && rm -rf /tmp/spike

RUN git clone https://github.com/riscv-software-src/riscv-pk.git /tmp/pk \
    && cd /tmp/pk && mkdir build && cd build \
    && ../configure --prefix=/usr/local --host=riscv64-unknown-elf \
    && make -j$(nproc) && make install \
    && rm -rf /tmp/pk

WORKDIR /workspace
