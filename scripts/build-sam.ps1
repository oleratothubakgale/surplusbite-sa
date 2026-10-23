$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$urlPackage = Join-Path $root "backend/url_package"
$processorPackage = Join-Path $root "backend/processor_package"

foreach ($packagePath in @($urlPackage, $processorPackage)) {
    if (Test-Path $packagePath) {
        Remove-Item $packagePath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $packagePath | Out-Null
}

Copy-Item "backend/upload_url_lambda.py" $urlPackage
Copy-Item "backend/lambda_function.py" $processorPackage

# Download Linux wheels for Lambda's Python 3.12 x86_64 runtime. This avoids
# packaging a Windows-native Pillow binary when Docker is unavailable.
python -m pip install `
    --only-binary=:all: `
    --platform manylinux_2_28_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --abi cp312 `
    --target $processorPackage `
    --requirement "backend/requirements.txt"

if ($LASTEXITCODE -ne 0) {
    throw "Could not install Lambda-compatible Python dependencies."
}

sam validate --lint --template-file template.yaml
if ($LASTEXITCODE -ne 0) {
    throw "SAM template validation failed."
}