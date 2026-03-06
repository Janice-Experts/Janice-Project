document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session');

    if (!sessionId) {
        document.getElementById('results-container').innerHTML = '<p>No session ID provided.</p>';
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${sessionId}/results?page_size=500`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to load results');
        }

        renderSummary(data);
        renderTable(data.rows, sessionId);
    } catch (err) {
        document.getElementById('results-container').innerHTML =
            `<p class="status error">Error: ${err.message}</p>`;
    }
});

function renderSummary(data) {
    document.getElementById('summary').innerHTML = `
        <div class="stats-row">
            <div class="stat-card blue">
                <div class="stat-number">${data.total}</div>
                <div class="stat-label">Total Claims / Totaal Eise</div>
            </div>
            <div class="stat-card red">
                <div class="stat-number">${data.rejected_count + (data.manual_count || 0)}</div>
                <div class="stat-label">Rejected Claims / Geweierde Eise</div>
            </div>
        </div>
    `;
}

function renderTable(rows, sessionId) {
    const container = document.getElementById('results-container');

    const rejected = rows.filter(r => r.status !== 'green');

    if (!rejected.length) {
        container.innerHTML = '<p style="color:#64748b">No rejected claims found.</p>';
        return;
    }

    let html = `
        <div class="corrections-section">
            <div class="section-title">Rejected Claims – Suggested Corrections / Geweierde Eise – Voorgestelde Regstellings</div>
            <div class="table-wrapper">
                <table class="cg-table">
                    <thead>
                        <tr>
                            <th>Claim ID</th>
                            <th>Procedure / Prosedure</th>
                            <th>ICD-10 Code</th>
                            <th>Error / Fout</th>
                            <th>Suggested Correction / Voorgestelde Regstelling</th>
                            <th>Accept? / Aanvaar?</th>
                        </tr>
                    </thead>
                    <tbody>`;

    for (const row of rejected) {
        const raw = row.raw_data || {};
        const firstIssue = (row.issues || [])[0];
        const errorMsg = firstIssue ? firstIssue.message : '';
        const firstSuggestion = firstIssue && firstIssue.suggestions && firstIssue.suggestions.length
            ? firstIssue.suggestions[0]
            : (raw[firstIssue && firstIssue.field] || '');
        const field = firstIssue ? firstIssue.field : '';

        html += `
                        <tr>
                            <td>${raw.ClaimID || ''}</td>
                            <td>${raw.CPT_Code || ''}</td>
                            <td>${raw.ICD_Code || ''}</td>
                            <td>${errorMsg}</td>
                            <td><input class="correction-input" data-row-id="${row.id}" data-field="${field}" value="${firstSuggestion}"></td>
                            <td><input type="checkbox" class="accept-checkbox" checked></td>
                        </tr>`;
    }

    html += `
                    </tbody>
                </table>
            </div>
            <div class="export-btn-wrap">
                <button id="export-btn" class="export-btn">Export Corrected Batch / Voer Gekorrigeerde Eise Uit</button>
            </div>
        </div>`;

    container.innerHTML = html;
    document.getElementById('export-btn').addEventListener('click', () => exportCSV(sessionId));
}

async function exportCSV(sessionId) {
    const corrections = {};

    document.querySelectorAll('.correction-input').forEach(input => {
        if (input.value) {
            const rowId = input.dataset.rowId;
            const field = input.dataset.field;
            if (!corrections[rowId]) corrections[rowId] = {};
            corrections[rowId][field] = input.value;
        }
    });

    await fetch(`/api/sessions/${sessionId}/corrections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corrections),
    });

    window.location.href = `/api/sessions/${sessionId}/export`;
}
