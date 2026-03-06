document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        renderSummaryCards(data.summary);
        renderChart(data.error_breakdown);
        renderSessionsTable(data.recent_sessions);
    } catch (err) {
        console.error('Dashboard error:', err);
    }
});

function renderSummaryCards(summary) {
    document.getElementById('summary-cards').innerHTML = `
        <div class="card">
            <div class="card-value">${summary.total_claims}</div>
            <div class="card-label">Total Claims</div>
        </div>
        <div class="card green">
            <div class="card-value">${summary.auto_fixed}</div>
            <div class="card-label">Auto-Fixed</div>
        </div>
        <div class="card yellow">
            <div class="card-value">${summary.needs_review}</div>
            <div class="card-label">Needs Review</div>
        </div>
        <div class="card red">
            <div class="card-value">${summary.rejected}</div>
            <div class="card-label">Rejected</div>
        </div>
    `;
}

function renderChart(breakdown) {
    const ctx = document.getElementById('errors-chart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Invalid ICD', 'Invalid CPT', 'Bad Modifier', 'Duplicates'],
            datasets: [{
                label: 'Error Count',
                data: [
                    breakdown.invalid_icd,
                    breakdown.invalid_cpt,
                    breakdown.bad_modifier,
                    breakdown.duplicates,
                ],
                backgroundColor: ['#e53e3e', '#dd6b20', '#d69e2e', '#6b46c1'],
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
    });
}

function renderSessionsTable(sessions) {
    const el = document.getElementById('sessions-table');

    if (!sessions.length) {
        el.innerHTML = '<p style="color:#718096">No sessions yet. Upload a CSV to get started.</p>';
        return;
    }

    let html = `<table>
        <thead><tr>
            <th>File</th>
            <th>Uploaded</th>
            <th>Total</th>
            <th>Auto-Fixed</th>
            <th>Needs Review</th>
            <th>Rejected</th>
            <th></th>
        </tr></thead>
        <tbody>`;

    for (const s of sessions) {
        const date = new Date(s.uploaded_at).toLocaleString();
        html += `<tr>
            <td>${s.filename}</td>
            <td>${date}</td>
            <td>${s.total_rows}</td>
            <td class="green-text">${s.auto_fixed_count}</td>
            <td class="yellow-text">${s.manual_count}</td>
            <td class="red-text">${s.rejected_count}</td>
            <td><a href="/results.html?session=${s.id}" class="btn btn-sm">View</a></td>
        </tr>`;
    }

    html += '</tbody></table>';
    el.innerHTML = html;
}
