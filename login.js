
const API_URL = "http://127.0.0.1:5000";

const loginForm = document.getElementById("loginForm");

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;
    const role = document.querySelector('input[name="role"]:checked').value;

    const button = document.getElementById("loginButton");
    const message = document.getElementById("loginMessage");

    button.disabled = true;
    button.textContent = "Signing in...";

    message.className = "message";
    message.textContent = "";

    try {
        const response = await fetch(`${API_URL}/api/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,
                password: password,
                role: role
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Login failed.");
        }

        const user = data.user;

        if (!user || user.role !== role) {
            throw new Error("Account type does not match.");
        }

        // Save logged-in user details
        localStorage.setItem("hirelens_user", JSON.stringify(user));
        localStorage.setItem("hirelens_user_id", user.id);
        localStorage.setItem("hirelens_role", user.role);

        message.textContent = "Login successful! Redirecting...";
        message.className = "message success";

        // Redirect according to account type
        setTimeout(() => {
            if (user.role === "candidate") {
                window.location.href = "candidate_dashboard.html";
            } else {
                window.location.href = "recruiter_dashboard.html";
            }
        }, 800);

    } catch (error) {
        message.textContent = error.message;
        message.className = "message error";
        button.disabled = false;
        button.innerHTML = 'Sign In <span>→</span>';
    }
});
