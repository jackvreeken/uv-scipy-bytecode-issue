docker buildx build --no-cache --build-arg SOURCE_DATE_EPOCH=0 --platform linux/amd64  -t scipy-bytecode-diff --output type=docker,rewrite-timestamp=true .
