FROM fedora:22

RUN dnf -y install python-pip && \
    dnf -y clean all

ADD . /opt/cached_property

WORKDIR /opt/cached_property

RUN pip install -r requirements.txt --use-mirrors

CMD py.test
