FROM alpine

RUN apk add --no-cache python3 git && \
        pip3 install git+https://github.com/StidOfficial/pytftp.git && \
        apk del git

COPY __main__.py /usr/bin/tftpd

RUN chmod +x /usr/bin/tftpd

CMD [ "tftpd" ]