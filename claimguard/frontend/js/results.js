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
        <div class="summary-cards">
            <div class="card">
                <div class="card-value">${data.total}</div>
                <div class="card-label">Total Claims</div>
            </div>
            <div class="card green">
                <div class="card-value">${data.auto_fixed_count}</div>
                <div class="card-label">Auto-Fixed</div>
            </div>
            <div class="card yellow">
                <div class="card-value">${data.manual_count}</div>
                <div class="card-label">Needs Review</div>
            </div>
            <div class="card red">
                <div class="card-value">${data.rejected_count}</div>
                <div class="card-label">Rejected</div>
            </div>
        </div>
        <div class="results-heading"><h2>${data.filename}</h2></div>
    `;
}

function renderTable(rows, sessionId) {
    const container = document.getElementById('results-container');

    if (!rows.length) {
        container.innerHTML = '<p>No rows found.</p>';
        return;
    }

    const keys = Object.keys(rows[0].raw_data);

    let html = `<div class="table-wrapper"><table>
        <thead><tr>
            <th>Row</th>
            <th>Status</th>
            ${keys.map(k => `<th>${k}</th>`).join('')}
            <th>Issues</th>
        </tr></thead>
        <tbody>`;

    for (const row of rows) {
        const issuesByField = {};
        for (const issue of (row.issues || [])) {
            issuesByField[issue.field] = issue;
        }

        html += `<tr class="row-${row.status}" data-row-id="${row.id}">`;
        html += `<td>${row.row}</td>`;
        html += `<td><span class="badge badge-${row.status}">${row.status.toUpperCase()}</span></td>`;

        for (const key of keys) {
            const issue = issuesByField[key];
            const correctedValue = row.corrections && row.corrections[key] ? row.corrections[key] : null;
            const rawValue = row.raw_data[key];

            if (issue && issue.suggestions && issue.suggestions.length > 0) {
                html += `<td>
                    <select class="correction-select" data-row-id="${row.id}" data-field="${key}">
                        <option value="">${rawValue} (select fix)</option>
                        ${issue.suggestions.map(s => `<option value="${s}">${s}</option>`).join('')}
                    </select>
                </td>`;
            } else if (correctedValue) {
                html += `<td><span class="auto-fixed" title="Auto-fixed from: ${rawValue}">${correctedValue} &#10003;</span></td>`;
            } else {
                html += `<td>${rawValue}</td>`;
            }
        }

        const issueMessages = (row.issues || [])
            .filter(i => !i.message?.startsWith('Auto-fixed'))
            .map(i => `<span class="issue-tag">${i.field}: ${i.message}</span>`)
            .join('');
        html += `<td class="issues-cell">${issueMessages}</td>`;
        html += '</tr>';
    }

    html += `</tbody></table></div>`;
    html += `<div class="export-bar">
        <button id="export-btn" class="btn btn-primary">Save Corrections &amp; Export CSV</button>
        <a href="/dashboard.html" class="btn btn-secondary">View Dashboard</a>
    </div>`;

    container.innerHTML = html;
    document.getElementById('export-btn').addEventListener('click', () => exportCSV(sessionId));
}

async function exportCSV(sessionId) {
    const corrections = {};

    document.querySelectorAll('.correction-select').forEach(select => {
        if (select.value) {
            const rowId = select.dataset.rowId;
            const field = select.dataset.field;
            if (!corrections[rowId]) corrections[rowId] = {};
            corrections[rowId][field] = select.value;
        }
    });

    await fetch(`/api/sessions/${sessionId}/corrections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corrections),
    });

    window.location.href = `/api/sessions/${sessionId}/export`;
}
