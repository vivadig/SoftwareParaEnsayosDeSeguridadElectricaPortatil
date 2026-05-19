FROM registry.access.redhat.com/ubi8/ubi-minimal

# Install Python and required tools
RUN microdnf install python3.11 python3.11-devel python3.11-pip gcc git tar make \
    systemd-devel autoconf automake libtool pkg-config && microdnf clean all

# Install uv
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod +x /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:$PATH"

# Set UV cache directory
ENV UV_CACHE_DIR=/tmp/uv-cache

# Build and install libusb from source
RUN git clone https://github.com/libusb/libusb.git /tmp/libusb && \
    cd /tmp/libusb && \
    ./bootstrap.sh && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/libusb

# Build and install hidapi from source (required for usbrelay)
RUN git clone https://github.com/libusb/hidapi.git /tmp/hidapi && \
    cd /tmp/hidapi && \
    ./bootstrap && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/hidapi

# Clone and build usbrelay (always gets latest version on build)
RUN git clone https://github.com/darrylb123/usbrelay.git /tmp/usbrelay && \
    cd /tmp/usbrelay && \
    make && \
    cp usbrelay /usr/local/bin/ && \
    cp libusbrelay.so.1.2 /usr/lib64/ && \
    ldconfig && \
    cd usbrelay_py && \
    python3.11 -m pip install --no-cache-dir build && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/usbrelay

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Copy and set entrypoint permissions
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set proper permissions
RUN chown -R 1001:0 /app/ && \
    chown -R 1001:0 /run && \
    chmod 777 /run && \
    chown -R 1001:0 /tmp/uv-cache && \
    chown 1001:0 /entrypoint.sh && \
    mkdir -p /app/test-results && \
    chown -R 1001:0 /app/test-results && \
    chmod 755 /app/test-results

USER 1001

ENTRYPOINT ["/entrypoint.sh"]

CMD ["help"]
