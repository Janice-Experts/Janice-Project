document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileNameEl = document.getElementById('file-name');
    const statusEl = document.getElementById('status');

    fileNameEl.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameEl.textContent = fileInput.files[0].name;
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) {
            showStatus('Please select a CSV file. / Kies asseblief \'n CSV-lêer.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        showStatus('Validating claims... / Besig om eise te valideer...', 'info');

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
