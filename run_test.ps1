param(
    [Parameter(Mandatory=$true)]
    [int]$BuildCount,
    [Parameter(Mandatory=$true)]
    [ValidateSet("uv", "compileall")]
    [string]$BuildType
)

# Determine dockerfile and output file based on BuildType
$dockerfile = if ($BuildType -eq "uv") { "Dockerfile.uv" } else { "Dockerfile.compileall" }
$outputFile = "build_digests_$BuildType.txt"

# Create empty file (or clear existing one)
"" | Out-File -FilePath $outputFile

# Create builder
docker buildx create --name mybuilder --driver docker-container --use

# Create an array to store the digests
$digests = @()

# Run the build N times
for ($i = 1; $i -le $BuildCount; $i++) {
    Write-Host "Build $i of $BuildCount..."
    
    # Run the build command and capture the output
    $output = docker buildx build --no-cache -f $dockerfile --build-arg SOURCE_DATE_EPOCH=0 --platform linux/amd64 -t scipy-test-1 --output type=docker,buildinfo=false,rewrite-timestamp=true . 2>&1
    
    # Get the image ID of the newly built image
    $imageId = docker images scipy-test-1 --quiet
    
    # Get the digest for the image
    $digest = docker inspect --format='{{.Id}}' $imageId
    
    # Create the digest entry and write it to file immediately
    $digestEntry = "$digest"
    $digestEntry | Out-File -FilePath $outputFile -Append
    
    Write-Host "Digest: $digest`n"
}

# Remove the final file write since we're writing incrementally now
Write-Host "Complete! Results saved to $outputFile"

docker buildx rm mybuilder
