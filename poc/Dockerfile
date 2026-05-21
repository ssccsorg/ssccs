FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# System packages including native RISC-V cross-compiler (aarch64 compatible)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    device-tree-compiler \
    wget \
    xz-utils \
    ca-certificates \
    gcc-riscv64-linux-gnu \
    binutils-riscv64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

# Rust installation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# RISC-V targets for Rust cross-compilation
RUN rustup target add riscv64imac-unknown-none-elf

# Alias so the riscv-pk build and our test scripts find the compiler
RUN ln -sf /usr/bin/riscv64-linux-gnu-gcc /usr/local/bin/riscv64-unknown-elf-gcc \
    && ln -sf /usr/bin/riscv64-linux-gnu-g++ /usr/local/bin/riscv64-unknown-elf-g++ \
    && ln -sf /usr/bin/riscv64-linux-gnu-ar /usr/local/bin/riscv64-unknown-elf-ar \
    && ln -sf /usr/bin/riscv64-linux-gnu-as /usr/local/bin/riscv64-unknown-elf-as \
    && ln -sf /usr/bin/riscv64-linux-gnu-ld /usr/local/bin/riscv64-unknown-elf-ld \
    && ln -sf /usr/bin/riscv64-linux-gnu-objdump /usr/local/bin/riscv64-unknown-elf-objdump \
    && ln -sf /usr/bin/riscv64-linux-gnu-objcopy /usr/local/bin/riscv64-unknown-elf-objcopy

# Verify cross-compiler
RUN echo 'int main(){}' | riscv64-unknown-elf-gcc -x c - -o /tmp/test && rm /tmp/test

# Spike from source
RUN git clone https://github.com/riscv-software-src/riscv-isa-sim.git /tmp/spike \
    && cd /tmp/spike && mkdir build && cd build \
    && ../configure --prefix=/usr/local && make -j$(nproc) && make install \
    && rm -rf /tmp/spike

# riscv-pk (proxy kernel) from source, cross-compiled for RISC-V
RUN git clone https://github.com/riscv-software-src/riscv-pk.git /tmp/pk \
    && cd /tmp/pk && mkdir build && cd build \
    && CC=riscv64-unknown-elf-gcc ../configure --prefix=/usr/local --host=riscv64-unknown-elf \
    && make -j$(nproc) && make install \
    && rm -rf /tmp/pk

# Verify pk binary
RUN test -f /usr/local/riscv64-unknown-elf/bin/pk

WORKDIR /workspace
