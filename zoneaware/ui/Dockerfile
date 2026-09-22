FROM registry.access.redhat.com/hi/python:3.14-builder AS base

RUN dnf -y install --setopt=tsflags=nodocs --setopt=install_weak_deps=0 --nodocs\
      autoconf automake bzip2 gcc-c++ gd-devel gdb git libcurl-devel \
      libpq-devel libxml2-devel libxslt-devel lsof make mariadb-connector-c-devel \
      openssl-devel patch procps-ng npm redhat-rpm-config sqlite-devel unzip wget which zlib-devel \
      python3 python3-devel; \
      python3 -m ensurepip ;\
      dnf -y clean all --enablerepo='*'

FROM base as builder
USER root
COPY requirements.txt /tmp/requirements.txt
RUN dnf -y --setopt=install_weak_deps=0 --nodocs --use-host-config \
      --installroot /output \
      install \
      glibc glibc-minimal-langpack libstdc++ \
      bash \
      python3 python3-packaging; \
      dnf -y clean all --enablerepo='*'

RUN pip3 install --prefix=/usr --root /output -r /tmp/requirements.txt

FROM registry.access.redhat.com/hi/python:3.14
COPY --from=builder /output/usr/bin/gunicorn /app/bin/gunicorn
COPY --from=builder /output /
COPY templates /app/templates
COPY app.py /app/app.py
COPY gunicorn_worker.py /app/gunicorn_worker.py

USER 1001
WORKDIR /app
ENV PATH=/usr/bin:/bin:/usr/sbin:/sbin:/app/bin
ENV PYTHONPATH=/app
ENV PYTHON_HISTORY_FILE=/tmp/.python_history
ENTRYPOINT [ "/app/bin/gunicorn" ]
CMD [ "--pythonpath", "/usr/bin/python3", "--bind", "0.0.0.0:8080", "app:app_factory", "--worker-class", "aiohttp.GunicornWebWorker", "--access-logfile", "-", "-c", "/app/gunicorn_worker.py"]

