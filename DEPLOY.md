# SurplusBite SAM deployment (existing-bucket setup)

## AWS resources this stack manages

- Two Python 3.12 Lambda functions: presigned upload URL generator and image processor.
- Least-privilege, SAM-generated execution roles, including narrowly prefix-scoped
   catalogue existence access.
- A new private, encrypted, versioned output bucket (retained when the stack is deleted).
- Function URL CORS restricted to the current CloudFront site origin.
- Permission for the source upload bucket to invoke the processor.

The frontend bucket and CloudFront distribution are reused. The source upload
bucket is `surplusbite-uploads-405034826598` in **eu-west-1**; an S3 bucket
notification and its Lambda target must be in the same region.

## Build and deploy (PowerShell)

1. Confirm the AWS CLI identity is the intended account: `aws sts get-caller-identity`.
2. From the repository root, run `./scripts/build-sam.ps1`.
   The script vendors Pillow's Linux x86_64 wheel into the processor package;
   Docker is not required for this Windows build. It validates the SAM template
   but intentionally does not run `sam build`, which can omit Linux native
   extensions when building on Windows.
3. Deploy `template.yaml` directly to `eu-west-1`, using stack name `surplusbite-dev`.
   For the first deployment, let SAM create/use its managed artifact bucket.
   Set `EnableRekognition=false` unless label detection is intentionally enabled.
4. Save the `UploadUrl`, `ImageProcessorFunctionName`, `SourceBucketName`, and
   `OutputBucketName` stack outputs.

## Finish the bucket and frontend integration

Run `./scripts/integrate-existing-site.ps1` from the repository root after the
stack deploy. It verifies the AWS account, scopes source-bucket CORS to the
CloudFront origin, configures an `s3:ObjectCreated:*` notification filtered to
`uploads/`, publishes the upload page assets alongside (not over) the existing
site files, invalidates their CloudFront paths, and tests the URL generator
without uploading a file. The script deliberately expects the existing account,
bucket, distribution, and stack names listed above.

Then upload one JPG and one PNG at `https://d19a31sgm2plos.cloudfront.net/upload.html`,
check the processor's CloudWatch log group,
   and confirm `thumbnails/` plus `catalogue/index.json` appear in the output
   bucket.

## Notes

- The deployed Function URL is public (`AuthType: NONE`) so browsers can call it;
  keep its CORS origin restricted and monitor usage/costs.
- S3 notifications are configured on the source bucket outside this stack to
   avoid CloudFormation taking ownership of and replacing its notification
   configuration. The integration script replaces that bucket's notification
   configuration; preserve any other consumers before running it again. Remove
   the notification before deleting the stack.
- The output bucket is private. The current upload page does not display the
  catalogue or thumbnails; serving them on the site requires a separate
  authorized CloudFront origin/access policy.