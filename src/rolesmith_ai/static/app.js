document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadJobs();
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadJobs();
    }, 30000);
});

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Update top counters
        animateValue('stat-total-jobs', 0, data.total_jobs, 1000);
        animateValue('stat-applied', 0, data.total_applied, 1000);
        
        const reviewCount = data.by_status['review_needed'] || 0;
        document.getElementById('stat-review').textContent = reviewCount;
        
        // Populate runs list
        const runsList = document.getElementById('runs-list');
        runsList.innerHTML = '';
        if (data.recent_runs.length === 0) {
            runsList.innerHTML = '<div class="run-item"><div style="color: var(--text-secondary)">No recent runs</div></div>';
        } else {
            data.recent_runs.forEach(run => {
                const date = new Date(run.started_at).toLocaleString();
                const statusClass = run.status === 'running' ? 'text-warning' : (run.status === 'success' ? 'text-gradient' : 'text-danger');
                
                runsList.innerHTML += `
                    <div class="run-item">
                        <div>
                            <div style="font-weight: 600">Run ${run.id.substring(0,8)}</div>
                            <div class="run-time">${date}</div>
                        </div>
                        <div class="badge badge-new ${statusClass}" style="background: rgba(255,255,255,0.05); border: none;">
                            ${run.status || 'unknown'}
                        </div>
                    </div>
                `;
            });
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function loadJobs() {
    try {
        const response = await fetch('/api/jobs');
        const jobs = await response.json();
        
        const tbody = document.getElementById('jobs-body');
        tbody.innerHTML = '';
        
        jobs.forEach(job => {
            // Determine badge class
            let badgeClass = 'badge-new';
            if (job.status === 'applied') badgeClass = 'badge-applied';
            else if (job.status === 'review_needed') badgeClass = 'badge-review';
            else if (job.status === 'rejected' || job.status === 'failed') badgeClass = 'badge-rejected';
            
            // Score styling
            const score = job.score || 0;
            let scoreClass = 'score-low';
            if (score >= 80) scoreClass = 'score-high';
            else if (score >= 60) scoreClass = 'score-med';
            
            const scoreHtml = job.score ? `<div class="score-ring ${scoreClass}">${score}</div>` : '<span style="color:var(--text-secondary)">-</span>';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight: 600; color: white; margin-bottom: 0.2rem;">${escapeHtml(job.title || 'Unknown Role')}</div>
                    <a href="${escapeHtml(job.url)}" target="_blank" style="color: var(--accent); font-size: 0.8rem; text-decoration: none;">View Job ↗</a>
                </td>
                <td style="font-weight: 500">${escapeHtml(job.company || 'Unknown')}</td>
                <td style="color: var(--text-secondary)">${escapeHtml(job.platform || '-')}</td>
                <td>${scoreHtml}</td>
                <td><span class="badge ${badgeClass}">${escapeHtml(job.status || 'new').replace('_', ' ')}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error fetching jobs:', error);
    }
}

// Helper to escape HTML and prevent XSS
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Helper for number animation
function animateValue(id, start, end, duration) {
    if (start === end) {
        document.getElementById(id).innerHTML = end;
        return;
    }
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        document.getElementById(id).innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
