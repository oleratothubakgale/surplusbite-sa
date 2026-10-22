# SurplusBite — Test Cases

Use this matrix to verify the system once the Cloud Engineer has deployed it to AWS.

| ID | Input / Action | Expected Result | Status |
|---|---|---|---|
| **TC-01** | Upload a valid JPG (e.g., 4032x3024 photo of an apple) | S3 Source Bucket receives file. Lambda triggers. Card (300x300) and Pin (96x96) saved to Output Bucket. Catalogue JSON updates. Rekognition returns category: `produce`. | ⬜ |
| **TC-02** | Upload a valid PNG (e.g., 1024x1024 RGBA image) | Image is converted to RGB, processed successfully, and saved. | ⬜ |
| **TC-03** | Upload a photo of a non-food item (e.g., a car or a selfie) | Lambda processes image, but Rekognition returns status: `no_food_detected`. Catalogue JSON reflects the warning. | ⬜ |
| **TC-04** | Upload a file named `corrupt.jpg` (plain text renamed to .jpg) | Lambda catches `UnidentifiedImageError`. Logs the error. Does NOT crash. No thumbnails are generated. | ⬜ |
| **TC-05** | Upload a `.gif` or `.pdf` file | Lambda rejects the file early based on the `VALID_EXTENSIONS` check. | ⬜ |
| **TC-06** | Rapidly upload 5 photos at the same time | All 5 photos process successfully. The JSON catalogue updates correctly (Last-Write-Wins). | ⬜ |