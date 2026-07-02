/* frontend/js/teacher_attendance.js */
let qrRotationTimer = null;
let liveFeedTimer = null;
let currentToken = null;
let qrCodeInstance = null;
let countdown = 15;
let sessionActive = false;

async function loadTeacherAttendance() {
    // Check if there is an active session
    // For simplicity, we just initialize the state
    document.getElementById('ta-setup-card').style.display = 'block';
    document.getElementById('ta-active-card').style.display = 'none';
}

async function startSession() {
    const payload = {
        department: document.getElementById('sess-dept').value,
        semester: parseInt(document.getElementById('sess-sem').value),
        section: document.getElementById('sess-sec').value,
        subject: document.getElementById('sess-sub').value,
        room: document.getElementById('sess-room').value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/start`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}` 
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            document.getElementById('ta-setup-card').style.display = 'none';
            document.getElementById('ta-active-card').style.display = 'block';
            document.getElementById('lbl-sub').textContent = payload.subject;
            document.getElementById('lbl-room').textContent = payload.room;
            
            currentToken = data.qr_token;
            sessionActive = true;
            renderQR(currentToken);
            startTimers();
        } else {
            taAlert('danger', data.detail || 'Failed to start session.');
        }
    } catch (err) {
        console.error(err);
        taAlert('danger', 'Network error.');
    }
}

function renderQR(token) {
    const container = document.getElementById('qrcode');
    if (!container) return;
    container.innerHTML = ''; // clear
    
    const tokenEl = document.getElementById('lbl-token');
    if (tokenEl) tokenEl.textContent = token;

    if (typeof QRCode === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';
        script.onload = () => {
            try {
                new QRCode(container, { text: token, width: 180, height: 180 });
            } catch (e) { console.error(e); }
        };
        document.head.appendChild(script);
    } else {
        try {
            new QRCode(container, { text: token, width: 180, height: 180 });
        } catch (e) { console.error(e); }
    }
}

function startTimers() {
    countdown = 15;
    document.getElementById('qr-timer').textContent = countdown;
    const bar = document.getElementById('qr-progress-bar');
    if (bar) bar.style.width = '100%';
    
    if(qrRotationTimer) clearInterval(qrRotationTimer);
    if(liveFeedTimer) clearInterval(liveFeedTimer);
    
    qrRotationTimer = setInterval(async () => {
        countdown--;
        if (countdown <= 0) {
            if(sessionActive) await rotateQR();
            countdown = 15;
        }
        const timerEl = document.getElementById('qr-timer');
        if (timerEl) timerEl.textContent = countdown;
        const pBar = document.getElementById('qr-progress-bar');
        if (pBar) pBar.style.width = `${Math.round((countdown / 15) * 100)}%`;
    }, 1000);
    
    liveFeedTimer = setInterval(fetchLiveFeed, 3000);
    fetchLiveFeed();
}

async function rotateQR() {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/rotate`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            currentToken = data.qr_token;
            renderQR(currentToken);
        }
    } catch (err) {
        console.error("Failed to rotate QR", err);
    }
}

async function fetchLiveFeed() {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/live`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            updateLiveTable(data.records);
        }
    } catch (err) {
        console.error("Failed to fetch live feed", err);
    }
}

function updateLiveTable(records) {
    const tbody = document.getElementById('live-table-body');
    document.getElementById('live-count').textContent = records.length;
    
    if(records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Waiting for scans...</td></tr>';
        return;
    }
    
    let html = '';
    records.forEach(r => {
        const d = new Date(r.timestamp);
        const time = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        html += `
            <tr>
                <td>${r.student_name}</td>
                <td>${r.usn}</td>
                <td><span class="badge bg-success">${r.status}</span></td>
                <td>${time}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

async function pauseSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/pause`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            sessionActive = false;
            document.getElementById('btn-pause').style.display = 'none';
            document.getElementById('btn-resume').style.display = 'block';
            
            const badge = document.getElementById('sess-status');
            badge.className = 'ta-status paused';
            badge.textContent = 'PAUSED';
            document.getElementById('qrcode').innerHTML = '<div class="text-center text-muted p-4">QR Paused</div>';
        }
    } catch (err) {}
}

async function resumeSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/resume`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            sessionActive = true;
            document.getElementById('btn-pause').style.display = 'block';
            document.getElementById('btn-resume').style.display = 'none';
            
            const badge = document.getElementById('sess-status');
            badge.className = 'ta-status active';
            badge.textContent = 'ACTIVE';
            
            // force rotate immediately
            await rotateQR();
            countdown = 15;
        }
    } catch (err) {}
}

async function endSession() {
    if(!confirm("Are you sure you want to end this session?")) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/end`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            clearInterval(qrRotationTimer);
            clearInterval(liveFeedTimer);
            sessionActive = false;
            
            document.getElementById('ta-setup-card').style.display = 'block';
            document.getElementById('ta-active-card').style.display = 'none';
            
            document.getElementById('live-table-body').innerHTML = '<tr><td colspan="4" class="text-center text-muted">Session ended.</td></tr>';
            
            taAlert('success', 'Session ended successfully.');
        }
    } catch (err) {}
}

function taAlert(type, msg) {
    const el = document.getElementById('ta-alert');
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 3000);
}

// Map the global function for layout view logic
window.renderTeacherAttendance = loadTeacherAttendance;
