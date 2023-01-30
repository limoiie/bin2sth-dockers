ARG UBUNTU_TAG=18.04
ARG VCPKG_TAG

FROM ubuntu:${UBUNTU_TAG}

# Avoid interactive dialogue
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary libraries
RUN apt-get update -o Acquire::http::proxy=false && \
    apt-get install -y -o Acquire::http::proxy=false \
    build-essential \
    cmake \
    curl \
    gcc \
    git \
    pkg-config \
    python \
    unzip \
    zip

# Configure vcpkg-compilation environment variables
ENV WORKSPACE=/code
ENV VCPKG_ROOT=${WORKSPACE}/vcpkg
ARG VCPKG_TAG

# Download, build and install vcpkg
WORKDIR ${WORKSPACE}
RUN git clone --branch ${VCPKG_TAG} https://github.com/limoiie/vcpkg.git
WORKDIR ${VCPKG_ROOT}
RUN ./bootstrap-vcpkg.sh && ./vcpkg integrate bash && \
    ./vcpkg register-compiler --c=$(which gcc) --cxx=$(which g++)

# Configure vcpkg-runtime environment variables
ENV VCPKG_RUN_DIR=${WORKSPACE}/run \
    VCPKG_EXTRA_DIR=${WORKSPACE}/conf \
    VCPKG_TOOL_DIR=${WORKSPACE}/tools
ENV VCPKG_DEFAULT_TRIPLET=x64-linux-dynamic \
    # input directories
    VCPKG_OVERLAY_TRIPLETS=${VCPKG_EXTRA_DIR}/triplets \
    VCPKG_COMPILERS=${VCPKG_EXTRA_DIR}/compilers \
    # output directories
    VCPKG_DOWNLOADS=${VCPKG_RUN_DIR}/downloads \
    VCPKG_BUILDTREES=${VCPKG_RUN_DIR}/buildtrees \
    VCPKG_PACKAGES=${VCPKG_RUN_DIR}/packages \
    VCPKG_INSTALL=${VCPKG_RUN_DIR}/installed

# Copy additional configurations
COPY extra ${VCPKG_EXTRA_DIR}

# Install build tools
RUN apt-get install -y -o Acquire::http::proxy=false \
    autoconf \
    autoconf-archive \
    bison \
    gettext \
    gnu-standards \
    libtool \
    python3 \
    python3-setuptools

WORKDIR ${VCPKG_ROOT}
ENTRYPOINT [ "/bin/bash" ]
