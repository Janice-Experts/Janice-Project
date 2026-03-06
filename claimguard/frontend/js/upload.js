document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const statusEl = document.getElementById('status');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            dropZone.querySelector('.drop-text').textContent = files[0].name;
        }
    });

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            dropZone.querySelector('.drop-text').textContent = fileInput.files[0].name;
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) {
            showStatus('Please select a CSV file.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        showStatus('Validating claims...', 'info');

        try {
            const response = await fetch('/api/validate', { method: 'POST', body: formData });
            const data = await response.json();

            if (!response.ok) {
                showStatus(data.detail || 'Validation failed.', 'error');
                return;
            }

            window.location.href = `/results.html?session=${data.session_id}`;
        } catch (err) {
            showStatus('Network error. Please try again.', 'error');
        }
    });

    function showStatus(msg, type) {
        statusEl.textContent = msg;
        statusEl.className = `status ${type}`;
        statusEl.style.display = 'block';
    }
});
