FROM alpine

COPY devutils/create_new_tag.sh /create_new_tag.sh

RUN apk update && apk add git curl bash jq

ENTRYPOINT ["/create_new_tag.sh"]
