
const API_BASE = "http://127.0.0.1:5000/api";

// Get logged-in user
function getStoredUser() {
    try {
        return JSON.parse(localStorage.getItem("hireLensUser")) || null;
    } catch (error) {
        return null;
    }
}

// Save user
function saveUser(user) {
    localStorage.setItem("hireLensUser", JSON.stringify(user));
}

// Show message
function showMessage(element, message, success = false) {
    if (!element) {
        alert(message);
        return;
    }

    element.textContent = message;
    element.style.color = success ? "#16a34a" : "#dc2626";
    element.style.display = "block";
}

// API request supporting GET, POST, PUT, PATCH
async function apiRequest(endpoint, data = {}, method = "POST") {
    const options = {
        method: method,
        headers: {
            "Content-Type": "application/json"
        }
    };

    if (method !== "GET" && method !== "HEAD") {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, options);

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            result.message || result.error || "Request failed. Please try again."
        );
    }

    return result;
}

// Extract user
function extractUser(result) {
    return result.user || result.data?.user || result.data || result;
}

// Open correct dashboard
function openDashboard(user) {
    saveUser(user);

    const role = String(user.role || "").toLowerCase();

    if (role === "recruiter") {
        window.location.href = "recruiter-dashboard.html";
    } else {
        window.location.href = "candidate_dashboard.html";
    }
}

// LOGIN AND REGISTER
document.addEventListener("DOMContentLoaded", function () {

    // LOGIN
    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const email = document.getElementById("loginEmail")?.value.trim();
            const password = document.getElementById("loginPassword")?.value;
            const selectedRole = document.querySelector(
                'input[name="role"]:checked'
            )?.value;

            const message = document.getElementById("loginMessage");
            const button = document.getElementById("loginButton");

            if (!email || !password || !selectedRole) {
                showMessage(message, "Please fill in all fields.");
                return;
            }

            if (button) {
                button.disabled = true;
                button.textContent = "Logging in...";
            }

            try {
                const result = await apiRequest("/login", {
                    email: email,
                    password: password,
                    role: selectedRole
                });

                if (result.success === false) {
                    throw new Error(result.message || "Login failed.");
                }

                const user = extractUser(result);

                if (!user || typeof user !== "object" || !user.email) {
                    throw new Error("Login response is missing user details.");
                }

                const actualRole = String(
                    user.role || selectedRole
                ).toLowerCase();

                if (actualRole !== selectedRole.toLowerCase()) {
                    throw new Error("Please select the correct account role.");
                }

                user.role = actualRole;
                openDashboard(user);

            } catch (error) {
                showMessage(message, error.message);
            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = "Login";
                }
            }
        });
    }

    // REGISTER
    const registerForm = document.getElementById("registerForm");

    if (registerForm) {
        registerForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const name = document.getElementById("registerName")?.value.trim();
            const email = document.getElementById("registerEmail")?.value.trim();
            const password = document.getElementById("registerPassword")?.value;
            const confirmPassword =
                document.getElementById("confirmPassword")?.value;

            const role = document.querySelector(
                'input[name="role"]:checked'
            )?.value;

            const company =
                document.getElementById("registerCompany")?.value.trim() || "";

            const message = document.getElementById("registerMessage");
            const button = document.getElementById("registerButton");

            if (!name || !email || !password || !role) {
                showMessage(message, "Please fill in all required fields.");
                return;
            }

            if (password.length < 6) {
                showMessage(message, "Password must be at least 6 characters.");
                return;
            }

            if (confirmPassword !== undefined && password !== confirmPassword) {
                showMessage(message, "Passwords do not match.");
                return;
            }

            if (button) {
                button.disabled = true;
                button.textContent = "Creating account...";
            }

            try {
                const result = await apiRequest("/register", {
                    name: name,
                    email: email,
                    password: password,
                    role: role,
                    company: company
                });

                if (result.success === false) {
                    throw new Error(result.message || "Registration failed.");
                }

                showMessage(
                    message,
                    "Registration successful! Redirecting to login...",
                    true
                );

                setTimeout(function () {
                    window.location.href = "login.html";
                }, 1000);

            } catch (error) {
                showMessage(message, error.message);
            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = "Create Account";
                }
            }
        });
    }

    // DISPLAY USER DETAILS
    const user = getStoredUser();

    if (user) {
        document.querySelectorAll("[data-user-name]").forEach(function (el) {
            el.textContent = user.name || "User";
        });

        document.querySelectorAll("[data-user-email]").forEach(function (el) {
            el.textContent = user.email || "";
        });

        document.querySelectorAll("[data-user-company]").forEach(function (el) {
            el.textContent = user.company || "";
        });
    }

    // LOGOUT
    document.querySelectorAll("[data-logout]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();

            localStorage.removeItem("hireLensUser");

            window.location.href = "login.html";
        });
    });

});
