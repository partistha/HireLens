
const API_URL = "http://127.0.0.1:5000";

const registerForm = document.getElementById("registerForm");

registerForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const name = document.getElementById("registerName").value.trim();
    const email = document.getElementById("registerEmail").value.trim();
    const password = document.getElementById("registerPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    const role = document.querySelector('input[name="role"]:checked').value;

    const button = document.getElementById("registerButton");
    const message = document.getElementById("registerMessage");

    // Check password confirmation
    if (password !== confirmPassword) {
        message.textContent = "Passwords do not match.";
        message.className = "message error";
        return;
    }

    if (event.defaultPrevented) return;

    button.disabled = true;
    button.textContent = "Creating Account...";
    message.textContent = "";
    message.className = "message";

    try {
        const response = await fetch(`${API_URL}/api/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                email: email,
                password: password,
                role: role
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || data.error || "Registration failed.");
        }

        message.textContent = "Account created successfully! Redirecting to login...";
        message.className = "message success";

        registerForm.reset();

        setTimeout(() => {
            window.location.href = "login.html";
        }, 1500);

    } catch (error) {
        message.textContent = error.message || "Unable to connect to server.";
        message.className = "message error";
        button.disabled = false;
        button.textContent = "Create Account →";
    }
});
