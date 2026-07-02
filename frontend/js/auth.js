// Load registration options on page load
document.addEventListener("DOMContentLoaded", () => {
    const sDept = document.getElementById("s-dept");
    if (sDept) {
        loadRegistrationOptions();
    }
});

async function loadRegistrationOptions() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/registration-options`);
        if (response.ok) {
            const data = await response.json();
            const deptSelect = document.getElementById("s-dept");
            const secSelect = document.getElementById("s-sec");
            const genderSelect = document.getElementById("s-gender");
            
            if (deptSelect) {
                deptSelect.innerHTML = '<option value="" disabled selected>Select</option>';
                data.departments.forEach(dept => {
                    deptSelect.innerHTML += `<option value="${dept.name}">${dept.name}</option>`;
                });
            }
            if (secSelect) {
                secSelect.innerHTML = '<option value="" disabled selected>Select</option>';
                data.sections.forEach(sec => {
                    secSelect.innerHTML += `<option value="${sec}">${sec}</option>`;
                });
            }
            if (genderSelect) {
                genderSelect.innerHTML = '<option value="" disabled selected>Select</option>';
                data.genders.forEach(gen => {
                    genderSelect.innerHTML += `<option value="${gen}">${gen}</option>`;
                });
            }
        }
    } catch (error) {
        console.error("Failed to load registration options", error);
    }
}

async function registerStudent(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = "Submitting...";
    btn.disabled = true;

    try {
        const formData = new FormData();
        formData.append("full_name", document.getElementById("s-name").value.trim());
        formData.append("email", document.getElementById("s-email").value.trim());
        formData.append("password", document.getElementById("s-pass").value);
        formData.append("confirm_password", document.getElementById("s-confirm-pass").value);
        formData.append("usn", document.getElementById("s-usn").value.trim());
        formData.append("department", document.getElementById("s-dept").value);

        const response = await fetch(`${API_BASE_URL}/auth/student/register`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message || "Registration successful!");
            setTimeout(() => {
                window.location.href = "signin.html";
            }, 2000);
        } else {
            let errorMsg = data.detail;
            if (Array.isArray(errorMsg)) {
                errorMsg = errorMsg.map(err => err.msg).join('\n');
            }
            alert(`Registration failed:\n${errorMsg}`);
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        alert("Network error: Could not connect to the server.");
        console.error(error);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function loginStudent(e, role) {
    e.preventDefault();

    if (role === 'teacher') {
        await loginTeacher(e);
        return;
    }

    const btn = document.getElementById("s-submit-btn");
    const originalText = btn.textContent;
    btn.textContent = "Signing in...";
    btn.disabled = true;
    const errEl = document.getElementById("s-error");
    if (errEl) errEl.classList.add("hidden");

    try {
        const email = document.getElementById("s-email").value.trim();
        const password = document.getElementById("s-pass").value;

        const response = await fetch(`${API_BASE_URL}/auth/student/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("token_type", data.token_type);
            localStorage.setItem("student", JSON.stringify(data.student));
            
            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 500);
        } else {
            if (errEl) {
                errEl.textContent = data.detail || "Invalid credentials. Please try again.";
                errEl.classList.remove("hidden");
            } else {
                alert(data.detail || "Invalid credentials.");
            }
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        if (errEl) {
            errEl.textContent = "Network error: Could not connect to the server.";
            errEl.classList.remove("hidden");
        } else {
            alert("Network error: Could not connect to the server.");
        }
        console.error(error);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function loginTeacher(e) {
    const btn = document.getElementById("t-submit-btn");
    const originalText = btn ? btn.textContent : 'Sign In as Teacher';
    if (btn) { btn.textContent = "Signing in..."; btn.disabled = true; }
    const errEl = document.getElementById("t-error");
    if (errEl) errEl.classList.add("hidden");

    try {
        const email = document.getElementById("t-email").value.trim();
        const password = document.getElementById("t-pass").value;

        const response = await fetch(`${API_BASE_URL}/teacher/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("token_type", data.token_type);
            // Store under 'teacher' key so layout.js detects the role
            localStorage.setItem("teacher", JSON.stringify(data.teacher));

            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 500);
        } else {
            if (errEl) {
                errEl.textContent = data.detail || "Invalid credentials. Please try again.";
                errEl.classList.remove("hidden");
            } else {
                alert(data.detail || "Invalid credentials.");
            }
            if (btn) { btn.textContent = originalText; btn.disabled = false; }
        }
    } catch (error) {
        if (errEl) {
            errEl.textContent = "Network error: Could not connect to the server.";
            errEl.classList.remove("hidden");
        } else {
            alert("Network error: Could not connect to the server.");
        }
        console.error(error);
        if (btn) { btn.textContent = originalText; btn.disabled = false; }
    }
}

function switchTab(role) {
    const tabStudent = document.getElementById('tab-student');
    const tabTeacher = document.getElementById('tab-teacher');
    if (tabStudent) tabStudent.classList.toggle('active', role === 'student');
    if (tabTeacher) tabTeacher.classList.toggle('active', role === 'teacher');

    const formStudent = document.getElementById('form-student');
    const formTeacher = document.getElementById('form-teacher');
    if (formStudent) formStudent.classList.toggle('hidden', role !== 'student');
    if (formTeacher) formTeacher.classList.toggle('hidden', role !== 'teacher');
    
    // Dynamic text for Sign In left panel
    const heroTitle = document.getElementById('hero-title');
    const heroSubtitle = document.getElementById('hero-subtitle');
    if (heroTitle && heroSubtitle) {
        if (role === 'student') {
            heroTitle.innerHTML = 'Welcome back.';
            heroSubtitle.innerHTML = 'Your classroom is waiting.<br>Sign in to access your personalised dashboard.';
        } else {
            heroTitle.innerHTML = 'Welcome back.';
            heroSubtitle.innerHTML = 'Manage attendance, classes and reports.<br>Sign in to access your dashboard.';
        }
    }
    
    // Clear errors when switching tabs
    if (typeof clearErrors === 'function') {
        clearErrors('s');
        clearErrors('t');
    }
}

function registerTeacher(e) {
    e.preventDefault();
    alert("Teacher registration is not implemented yet.");
}

/* ── Show / hide password ── */
function togglePass(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.textContent = show ? '🙈' : '👁';
}

/* ── Helpers ── */
function setFieldError(inputId, msg) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.classList.add('input-error');
    let hint = document.getElementById(inputId + '-hint');
    if (!hint) {
        hint = document.createElement('span');
        hint.className = 'field-hint';
        hint.id = inputId + '-hint';
        const wrap = input.closest('.password-wrap');
        wrap ? wrap.after(hint) : input.after(hint);
    }
    hint.textContent = msg;
}

function clearFieldError(inputId) {
    const input = document.getElementById(inputId);
    if (input) input.classList.remove('input-error');
    const hint = document.getElementById(inputId + '-hint');
    if (hint) hint.textContent = '';
}

function clearErrors(prefix) {
    clearFieldError(prefix + '-email');
    clearFieldError(prefix + '-pass');
    const errEl = document.getElementById(prefix + '-error');
    if (errEl) errEl.classList.add('hidden');
}
