/**
 * frontend/js/face.js
 * EduSync — Smart Campus ERP | Face Registration Module
 */

let videoStream = null;
let capturedImages = []; // Array of { stepIndex, dataUrl, fileBlob }
const TOTAL_CAPTURES = 8;

const INSTRUCTIONS = [
    "Look straight",
    "Turn slight left",
    "Turn full left",
    "Turn slight right",
    "Turn full right",
    "Look slightly up",
    "Look slightly down",
    "Blink naturally / Neutral"
];

/* ── Entry Point (called by layout.js) ──────────────────────────────────── */
async function loadFacePage() {
    // Reset state
    capturedImages = [];
    if (videoStream) {
        stopCamera();
    }
    
    document.getElementById('face-loading').style.display = 'block';
    document.getElementById('face-status-view').style.display = 'none';
    document.getElementById('face-register-view').style.display = 'none';
    faceAlertHide();

    try {
        const response = await fetch(`${API_BASE_URL}/student/face/status`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        if (response.status === 401) {
            window.signOut();
            return;
        }

        const data = await response.json();
        
        document.getElementById('face-loading').style.display = 'none';

        if (data.is_registered) {
            // Already registered
            showStatusView(data);
        } else {
            // Not registered, show status view first with register button
            showStatusView(data);
        }
        
    } catch (err) {
        console.error(err);
        document.getElementById('face-loading').style.display = 'none';
        faceAlert('danger', "Failed to load face registration status.");
    }
}

/* ── Views ─────────────────────────────────────────────────────────────── */
function showStatusView(data) {
    document.getElementById('face-status-view').style.display = 'block';
    
    const badge = document.getElementById('face-status-badge');
    if (data.status === 'Reset Requested') {
        badge.className = "status-badge-lg unregistered";
        badge.textContent = "⏳ Reset Requested";
        document.getElementById('registered-actions').style.display = 'block';
        document.getElementById('unregistered-actions').style.display = 'none';
        document.getElementById('btn-request-reset').disabled = true;
        document.getElementById('btn-request-reset').textContent = "Request Pending";
    } else if (data.is_registered) {
        badge.className = "status-badge-lg registered";
        badge.textContent = "✅ Registered";
        document.getElementById('registered-actions').style.display = 'block';
        document.getElementById('unregistered-actions').style.display = 'none';
        document.getElementById('btn-request-reset').disabled = false;
        document.getElementById('btn-request-reset').textContent = "Request Reset";
    } else {
        badge.className = "status-badge-lg unregistered";
        badge.textContent = "❌ Not Registered";
        document.getElementById('registered-actions').style.display = 'none';
        document.getElementById('unregistered-actions').style.display = 'block';
    }
    
    document.getElementById('fs-status').textContent = data.status;
    document.getElementById('fs-images').textContent = `${data.images_captured} / 8`;
    
    // Add quality text if registered
    const qLabel = document.getElementById('fs-quality');
    if(qLabel) {
        qLabel.textContent = data.is_registered ? "Excellent" : "—";
    }

    document.getElementById('fs-version').textContent = data.version || "—";
    
    if (data.registration_date) {
        const d = new Date(data.registration_date);
        document.getElementById('fs-date').textContent = d.toLocaleDateString('en-IN', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    }
}

function showRegisterView() {
    document.getElementById('face-status-view').style.display = 'none';
    document.getElementById('face-register-view').style.display = 'block';
    renderThumbnails();
    updateProgress();
    startCamera();
}

/* ── Camera Logic ──────────────────────────────────────────────────────── */
async function startCamera() {
    const video = document.getElementById('webcam');
    const instruction = document.getElementById('camera-instruction');
    const btnCapture = document.getElementById('btn-capture');
    
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" } 
        });
        video.srcObject = videoStream;
        
        video.onloadedmetadata = () => {
            instruction.textContent = getNextInstruction();
            btnCapture.disabled = false;
        };
    } catch (err) {
        console.error("Camera access denied or unavailable", err);
        instruction.textContent = "Camera access denied. Please allow permissions.";
        btnCapture.disabled = true;
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
}

/* ── Capture Flow ──────────────────────────────────────────────────────── */
function getNextInstruction() {
    if (capturedImages.length >= TOTAL_CAPTURES) {
        return "All captures complete! Ready to submit.";
    }
    return INSTRUCTIONS[capturedImages.length];
}

async function captureFrame() {
    if (capturedImages.length >= TOTAL_CAPTURES) return;
    
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('capture-canvas');
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    
    // If video is mirrored in CSS (transform: scaleX(-1)), we might want to flip it on canvas too
    // so the saved image looks like what the user saw.
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to JPEG base64
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    
    // Convert dataUrl to Blob for submission
    const res = await fetch(dataUrl);
    const blob = await res.blob();
    
    capturedImages.push({
        stepIndex: capturedImages.length,
        dataUrl: dataUrl,
        fileBlob: blob
    });
    
    updateProgress();
    renderThumbnails();
    
    const instruction = document.getElementById('camera-instruction');
    const btnCapture = document.getElementById('btn-capture');
    
    instruction.textContent = getNextInstruction();
    
    if (capturedImages.length >= TOTAL_CAPTURES) {
        btnCapture.disabled = true;
        document.getElementById('btn-submit').style.display = 'block';
    }
    document.getElementById('btn-restart').style.display = 'block';
}

function deleteCapture(index) {
    capturedImages.splice(index, 1);
    
    updateProgress();
    renderThumbnails();
    
    document.getElementById('camera-instruction').textContent = getNextInstruction();
    document.getElementById('btn-capture').disabled = false;
    document.getElementById('btn-submit').style.display = 'none';
    
    if (capturedImages.length === 0) {
        document.getElementById('btn-restart').style.display = 'none';
    }
}

function restartCapture() {
    capturedImages = [];
    updateProgress();
    renderThumbnails();
    
    document.getElementById('camera-instruction').textContent = getNextInstruction();
    document.getElementById('btn-capture').disabled = false;
    document.getElementById('btn-submit').style.display = 'none';
    document.getElementById('btn-restart').style.display = 'none';
}

function updateProgress() {
    const current = capturedImages.length;
    const pct = (current / TOTAL_CAPTURES) * 100;
    
    document.getElementById('face-progress-fill').style.width = `${pct}%`;
    document.getElementById('face-progress-text').textContent = 
        current === TOTAL_CAPTURES 
        ? "Capture complete! You can submit now." 
        : `Step ${current + 1} of 8: ${INSTRUCTIONS[current]}`;
}

function renderThumbnails() {
    const grid = document.getElementById('thumbnail-grid');
    let html = '';
    
    for (let i = 0; i < TOTAL_CAPTURES; i++) {
        if (i < capturedImages.length) {
            html += `
                <div class="thumbnail-item">
                    <img src="${capturedImages[i].dataUrl}" alt="Capture ${i+1}">
                    <button class="thumbnail-delete" onclick="deleteCapture(${i})" title="Delete image">✕</button>
                </div>
            `;
        } else {
            html += `
                <div class="thumbnail-item thumbnail-placeholder">
                    ${i + 1}
                </div>
            `;
        }
    }
    
    grid.innerHTML = html;
}

/* ── Submission ────────────────────────────────────────────────────────── */
async function submitFaceData() {
    if (capturedImages.length !== TOTAL_CAPTURES) return;
    
    const btn = document.getElementById('btn-submit');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Submitting...';
    btn.disabled = true;
    faceAlertHide();
    
    const formData = new FormData();
    capturedImages.forEach((cap, i) => {
        // Append as file
        formData.append('images', cap.fileBlob, `face_${i+1}.jpg`);
    });
    
    try {
        const response = await fetch(`${API_BASE_URL}/student/face/register`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update local storage student to reflect registration
            let student = JSON.parse(localStorage.getItem('student') || '{}');
            student.face_registered = true;
            localStorage.setItem('student', JSON.stringify(student));
            
            // Reload page state
            await loadFacePage();
            faceAlert('success', "✅ Face registration successful!");
            
            // Update the sidebar strip & dashboard UI globally
            if (typeof refreshDashboardFromAPI === 'function') {
                refreshDashboardFromAPI();
            } else if (typeof currentUser !== 'undefined') {
                currentUser.face_registered = true;
                if (typeof updateUserStrip === 'function') updateUserStrip();
            }
        } else {
            throw new Error(data.detail || "Registration failed");
        }
        
    } catch (err) {
        console.error(err);
        faceAlert('danger', `❌ Error: ${err.message}`);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function requestFaceReset() {
    const btn = document.getElementById('btn-request-reset');
    btn.disabled = true;
    btn.textContent = 'Requesting...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/student/face/request-reset`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            faceAlert('success', `✅ ${data.message}`);
            await loadFacePage();
        } else {
            throw new Error(data.detail || "Failed to request reset.");
        }
    } catch (err) {
        console.error(err);
        faceAlert('danger', `❌ Error: ${err.message}`);
        btn.disabled = false;
        btn.textContent = 'Request Reset';
    }
}

/* ── Helpers ───────────────────────────────────────────────────────────── */
function faceAlert(type, msg) {
    const el = document.getElementById('face-alert');
    if (!el) return;
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
}

function faceAlertHide() {
    const el = document.getElementById('face-alert');
    if (el) el.style.display = 'none';
}
