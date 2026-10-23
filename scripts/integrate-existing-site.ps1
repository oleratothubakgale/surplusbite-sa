$ErrorActionPreference = "Stop"

$region = "eu-west-1"
$stackName = "surplusbite-dev"
$frontendBucket = "surplusbite-frontend-405034826598"
$distributionId = "E207WXFOU8ZGXL"

$identity = aws sts get-caller-identity --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not determine the AWS identity." }
if ($identity.Account -ne "405034826598") {
    throw "Expected AWS account 405034826598 but CLI is authenticated to $($identity.Account)."
}

$stack = aws cloudformation describe-stacks --stack-name $stackName --region $region --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not read stack $stackName in $region." }
$outputs = @{}
foreach ($output in $stack.Stacks[0].Outputs) { $outputs[$output.OutputKey] = $output.OutputValue }

$sourceBucket = $outputs.SourceBucketName
$origin = $outputs.FrontendOrigin
$uploadUrl = $outputs.UploadUrl
$processorName = $outputs.ImageProcessorFunctionName
if (-not $sourceBucket -or -not $origin -or -not $uploadUrl -or -not $processorName) {
    throw "Required stack outputs are missing."
}

$tempCors = Join-Path $env:TEMP "surplusbite-source-cors.json"
$tempNotification = Join-Path $env:TEMP "surplusbite-source-notification.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
try {
    $cors = @{
        CORSRules = @(
            @{
                AllowedHeaders = @("Content-Type")
                AllowedMethods = @("PUT")
                AllowedOrigins = @($origin)
                MaxAgeSeconds = 3600
            }
        )
    }
    [System.IO.File]::WriteAllText($tempCors, ($cors | ConvertTo-Json -Depth 8), $utf8NoBom)

    $processorArn = "arn:aws:lambda:${region}:$($identity.Account):function:$processorName"
    $notification = @{
        LambdaFunctionConfigurations = @(
            @{
                Id = "SurplusBiteImageProcessor"
                LambdaFunctionArn = $processorArn
                Events = @("s3:ObjectCreated:*")
                Filter = @{
                    Key = @{
                        FilterRules = @(@{ Name = "prefix"; Value = "uploads/" })
                    }
                }
            }
        )
    }
    [System.IO.File]::WriteAllText($tempNotification, ($notification | ConvertTo-Json -Depth 8), $utf8NoBom)

    aws s3api put-bucket-cors --bucket $sourceBucket --region $region --cors-configuration "file://$tempCors"
    if ($LASTEXITCODE -ne 0) { throw "Could not configure source-bucket CORS." }

    aws s3api put-bucket-notification-configuration --bucket $sourceBucket --region $region --notification-configuration "file://$tempNotification"
    if ($LASTEXITCODE -ne 0) { throw "Could not configure the source-bucket S3 event notification." }

    $frontendPath = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"
    aws s3 cp (Join-Path $frontendPath "upload.html") "s3://${frontendBucket}/upload.html" --region $region --content-type "text/html; charset=utf-8"
    if ($LASTEXITCODE -ne 0) { throw "Could not publish upload.html." }
    aws s3 cp (Join-Path $frontendPath "upload.html") "s3://${frontendBucket}/index.html" --region $region --content-type "text/html; charset=utf-8"
    if ($LASTEXITCODE -ne 0) { throw "Could not publish upload.html as the site homepage." }
    aws s3 cp (Join-Path $frontendPath "styles.css") "s3://${frontendBucket}/styles.css" --region $region --content-type "text/css; charset=utf-8"
    if ($LASTEXITCODE -ne 0) { throw "Could not publish styles.css." }
    aws s3 cp (Join-Path $frontendPath "index.js") "s3://${frontendBucket}/index.js" --region $region --content-type "application/javascript; charset=utf-8"
    if ($LASTEXITCODE -ne 0) { throw "Could not publish index.js." }

    aws cloudfront create-invalidation --distribution-id $distributionId --paths "/" "/index.html" "/upload.html" "/styles.css" "/index.js" --output json
    if ($LASTEXITCODE -ne 0) { throw "Could not invalidate CloudFront cache." }

    $probe = Invoke-RestMethod -Method Get -Uri ($uploadUrl + "?filename=deployment-check.jpg")
    if (-not $probe.upload_url -or -not $probe.key.StartsWith("uploads/")) {
        throw "Function URL returned an unexpected response."
    }

    Write-Host "Integration complete. Upload page: $origin/upload.html"
    Write-Host "Function URL returned a presigned URL successfully. No test image was uploaded."
}
finally {
    Remove-Item $tempCors, $tempNotification -Force -ErrorAction SilentlyContinue
}
