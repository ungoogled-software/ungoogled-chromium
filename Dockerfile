FROM alpine

COPY devutils/create_new_tag.sh /create_new_tag.sh

ENTRYPOINT ["/create_new_tag.sh"]
