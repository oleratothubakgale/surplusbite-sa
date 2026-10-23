    // Set this to the UploadUrl output from the deployed SAM stack.
    const API_URL = "https://gg2pixet4ojrmgcqfthhlaef740vqscd.lambda-url.eu-west-1.on.aws/";

        const card = document.getElementById('ui-card');
        const fileInput = document.getElementById('file-input');
        const dropZone = document.getElementById('drop-zone');
        const fileLabel = document.getElementById('file-label');
        const uploadBtn = document.getElementById('upload-btn');
        const statusDiv = document.getElementById('status');
        
        let selectedFile = null;

        /* =========================================
           MOUSE ANIMATION: 3D Parallax Tilt
           ========================================= */
        // Only apply 3D tilt on devices with a mouse (prevents mobile weirdness)
        if (window.matchMedia("(pointer: fine)").matches) {
            document.addEventListener('mousemove', (e) => {
                const xAxis = (window.innerWidth / 2 - e.pageX) / 25;
                const yAxis = (window.innerHeight / 2 - e.pageY) / 25;
                card.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
            });

            // Reset when mouse leaves window
            document.addEventListener('mouseleave', () => {
                card.style.transform = `rotateY(0deg) rotateX(0deg)`;
                card.style.transition = "transform 0.5s ease";
            });
            
            document.addEventListener('mouseenter', () => {
                card.style.transition = "transform 0.1s ease-out";
            });
        }

        /* =========================================
           FILE SELECTION MICRO-INTERACTIONS
           ========================================= */
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                fileLabel.textContent = selectedFile.name;
                dropZone.classList.add('has-file');
                uploadBtn.disabled = false;
                
                // Reset status
                statusDiv.className = "";
                statusDiv.textContent = "";
            }
        });

        /* =========================================
           UPLOAD LOGIC & LOADING ANIMATION
           ========================================= */
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;

            if (!API_URL.startsWith('https://')) {
                statusDiv.textContent = "Upload service is not configured yet.";
                statusDiv.className = "error show";
                return;
            }

            // Trigger Loading State
            uploadBtn.disabled = true;
            uploadBtn.classList.add('loading');
            card.classList.add('uploading');
            statusDiv.className = "";
            statusDiv.textContent = "Securing connection...";
            statusDiv.classList.add('show');

            try {
                // 1. Get presigned URL from our API
                const response = await fetch(`${API_URL}?filename=${encodeURIComponent(selectedFile.name)}`);
                if (!response.ok) throw new Error("Failed to get upload URL");
                
                const data = await response.json();
                
                statusDiv.textContent = "Uploading image to the cloud...";

                // 2. Upload the file directly to S3
                const uploadResponse = await fetch(data.upload_url, {
                    method: 'PUT',
                    headers: { 'Content-Type': selectedFile.type },
                    body: selectedFile
                });

                if (!uploadResponse.ok) throw new Error("Upload failed");

                // 3. Success!
                statusDiv.textContent = "Success! Your photo is being processed.";
                statusDiv.className = "success show";
                
                // Reset UI
                setTimeout(() => {
                    fileLabel.textContent = "Tap to select another photo";
                    dropZone.classList.remove('has-file');
                    uploadBtn.disabled = true;
                    selectedFile = null;
                    fileInput.value = "";
                }, 1000);

            } catch (error) {
                console.error(error);
                statusDiv.textContent = "Error: " + error.message;
                statusDiv.className = "error show";
                uploadBtn.disabled = false;
            } finally {
                // Remove Loading State
                uploadBtn.classList.remove('loading');
                card.classList.remove('uploading');
            }
        });