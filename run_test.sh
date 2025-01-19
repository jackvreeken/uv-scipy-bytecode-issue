#!/bin/bash

# Function to show usage
usage() {
    echo "Usage: $0 -c BUILD_COUNT -t BUILD_TYPE"
    echo "BUILD_TYPE must be either 'uv' or 'compileall'"
    exit 1
}

# Parse command line arguments
while getopts "c:t:" opt; do
    case $opt in
        c) BUILD_COUNT="$OPTARG";;
        t) BUILD_TYPE="$OPTARG";;
        *) usage;;
    esac
done

# Validate required arguments
if [ -z "$BUILD_COUNT" ] || [ -z "$BUILD_TYPE" ]; then
    usage
fi

# Validate BUILD_TYPE
if [ "$BUILD_TYPE" != "uv" ] && [ "$BUILD_TYPE" != "compileall" ]; then
    echo "Error: BUILD_TYPE must be either 'uv' or 'compileall'"
    exit 1
fi

# Determine dockerfile and output file based on BUILD_TYPE
dockerfile="Dockerfile.$BUILD_TYPE"
output_file="build_digests_${BUILD_TYPE}.txt"

# Create empty file (or clear existing one)
: > "$output_file"

docker buildx create --name mybuilder --driver docker-container --use

# Run the build N times
for ((i=1; i<=BUILD_COUNT; i++)); do
    echo "Build $i of $BUILD_COUNT..."
    
    # Run the build command and capture the output
    docker buildx build --no-cache -f "$dockerfile" \
        --build-arg SOURCE_DATE_EPOCH=0 \
        --platform linux/amd64 \
        -t scipy-test-1 \
        --output type=docker,buildinfo=false,rewrite-timestamp=true . >/dev/null 2>&1
    
    # Get the image ID and digest
    image_id=$(docker images scipy-test-1 --quiet)
    digest=$(docker inspect --format='{{.Id}}' "$image_id")
    
    # Write digest to file
    echo "$digest" >> "$output_file"
    
    echo "Digest: $digest"
    echo
done

echo "Complete! Results saved to $output_file"

docker buildx rm mybuilder
