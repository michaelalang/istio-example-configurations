FROM registry.fedoraproject.org/fedora:43

# Install Squid and OpenSSL
RUN dnf -y install squid openssl && dnf clean all

# Create the parent directory explicitly so the certgen tool doesn't fail
RUN mkdir -p /var/lib/squid

# Initialize the SSL certificate database for dynamic cert generation
RUN /usr/lib64/squid/security_file_certgen -c -s /var/lib/squid/ssl_db -M 4MB

# Copy your configuration file
COPY squid.conf /etc/squid/squid.conf

# Ensure the squid user owns all the necessary directories
RUN chown -R squid:squid /var/spool/squid /etc/squid /var/log/squid /var/lib/squid && \
    chmod -R 700 /var/lib/squid/ssl_db

# Run as the unprivileged squid user
USER squid

EXPOSE 8080

# At runtime: first initialize the cache dirs (squid -z), then start the proxy process
CMD ["/bin/sh", "-c", "squid -N -z && exec squid -N -d 1"]
