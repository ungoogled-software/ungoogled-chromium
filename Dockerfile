FROM alpine

COPY devutils/create_new_tag.sh /create_new_tag.sh

RUN apk update && apk add git curl bash

ENTRYPOINT ["/create_new_tag.sh"]
