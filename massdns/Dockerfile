FROM alpine:3.19

RUN apk add --no-cache git build-base

WORKDIR /tmp/massdns
RUN git clone --depth 1 https://github.com/blechschmidt/massdns.git .
RUN make
RUN install -m 0755 bin/massdns /usr/local/bin/massdns

VOLUME ["/opt/massdns"]

CMD ["sh", "-c", "cp /usr/local/bin/massdns /opt/massdns/massdns && chmod +x /opt/massdns/massdns && exec tail -f /dev/null"]
