
/* =========================================================
   HIRELENS - FRONTEND JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       LOGIN - CONNECTED TO FLASK BACKEND
       ===================================================== */

    const recruiterRoleBtn =
        document.getElementById("recruiterRoleBtn");

    const candidateRoleBtn =
        document.getElementById("candidateRoleBtn");

    const loginForm =
        document.getElementById("loginForm");

    let selectedRole = "recruiter";

    // Select account type
    if (recruiterRoleBtn && candidateRoleBtn) {

        recruiterRoleBtn.addEventListener("click", function () {
            selectedRole = "recruiter";
            recruiterRoleBtn.classList.add("active");
            candidateRoleBtn.classList.remove("active");
        });

        candidateRoleBtn.addEventListener("click", function () {
            selectedRole = "candidate";
            candidateRoleBtn.classList.add("active");
            recruiterRoleBtn.classList.remove("active");
        });

    }

    // Login form
    if (loginForm) {

        loginForm.addEventListener("submit", async function (event) {

            event.preventDefault();

            const emailInput =
                document.getElementById("loginEmail");

            const passwordInput =
                document.getElementById("loginPassword");

            if (!emailInput || !passwordInput) {
                alert("Login form fields were not found.");
                return;
            }

            const email = emailInput.value.trim();
            const password = passwordInput.value;

            if (!email || !password) {
                alert("Please enter your email and password.");
                return;
            }

            const submitButton = loginForm.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (submitButton) {
                submitButton.disabled = true;
            }

            try {

                const response = await fetch(
                    "http://127.0.0.1:5000/api/login",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            email: email,
                            password: password,
                            role: selectedRole
                        })
                    }
                );

                const result = await response.json();

                // Reject incorrect credentials
                if (!response.ok) {
                    alert(
                        result.error ||
                        "Login failed. Please check your details."
                    );
                    return;
                }

                // Save logged-in user's basic information
                localStorage.setItem(
                    "hireLensUser",
                    JSON.stringify(result.user)
                );

                alert("Login successful! Welcome to HireLens.");

                // Redirect according to account type
                if (result.user.role === "recruiter") {
                    window.location.href = "dashboard.html";
                } else {
                    window.location.href = "candidate-dashboard.html";
                }

            } catch (error) {

                console.error("Login error:", error);

                alert(
                    "Cannot connect to HireLens backend. " +
                    "Please make sure Flask is running."
                );

            } finally {

                if (submitButton) {
                    submitButton.disabled = false;
                }

            }

        });

    }


    /* =====================================================
       RECRUITER REGISTRATION
       CONNECTED TO FLASK BACKEND
       ===================================================== */

    const registerForm =
        document.getElementById("registerForm");

    if (registerForm) {

        registerForm.addEventListener("submit", async function (event) {

            event.preventDefault();

            const name =
                document.getElementById("fullName")?.value.trim();

            const company =
                document.getElementById("company")?.value.trim();

            const email =
                document.getElementById("registerEmail")?.value.trim();

            const phone =
                document.getElementById("phone")?.value.trim();

            const password =
                document.getElementById("registerPassword")?.value;

            const confirmPassword =
                document.getElementById("confirmPassword")?.value;

            const termsCheckbox =
                document.getElementById("termsCheckbox");

            if (
                !name ||
                !company ||
                !email ||
                !phone ||
                !password ||
                !confirmPassword ||
                !termsCheckbox
            ) {
                alert("Please complete all required fields.");
                return;
            }

            if (!termsCheckbox.checked) {
                alert("Please accept the prototype terms.");
                return;
            }

            if (password.length < 8) {
                alert("Password must contain at least 8 characters.");
                return;
            }

            if (password !== confirmPassword) {
                alert("Passwords do not match.");
                return;
            }

            const registerButton = registerForm.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (registerButton) {
                registerButton.disabled = true;
            }

            try {

                const response = await fetch(
                    "http://127.0.0.1:5000/api/register",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            name: name,
                            email: email,
                            password: password,
                            role: "recruiter"
                        })
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    alert(
                        result.error ||
                        "Registration failed. Please try again."
                    );
                    return;
                }

                // Save additional demo information locally
                const recruiterData = {
                    name: name,
                    company: company,
                    email: email,
                    phone: phone
                };

                localStorage.setItem(
                    "hireLensRecruiter",
                    JSON.stringify(recruiterData)
                );

                alert(
                    "Recruiter account created successfully! " +
                    "Please log in."
                );

                window.location.href = "login.html";

            } catch (error) {

                console.error("Registration error:", error);

                alert(
                    "Cannot connect to HireLens backend. " +
                    "Please make sure Flask is running."
                );

            } finally {

                if (registerButton) {
                    registerButton.disabled = false;
                }

            }

        });

    }


    /* =====================================================
       SMOOTH NAVIGATION
       ===================================================== */

    const navLinks =
        document.querySelectorAll('a[href^="#"]');

    navLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const targetId = this.getAttribute("href");

            if (targetId && targetId !== "#") {

                const target = document.querySelector(targetId);

                if (target) {
                    event.preventDefault();

                    target.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }

            }

        });

    });


    /* =====================================================
       SCROLL REVEAL ANIMATIONS
       ===================================================== */

    const revealElements =
        document.querySelectorAll(
            ".solution-card, .feature-card, .workflow-step"
        );

    if ("IntersectionObserver" in window) {

        const revealObserver = new IntersectionObserver(
            function (entries) {

                entries.forEach(function (entry) {

                    if (entry.isIntersecting) {

                        entry.target.style.opacity = "1";

                        entry.target.style.transform =
                            "translateY(0)";

                        revealObserver.unobserve(entry.target);

                    }

                });

            },
            {
                threshold: 0.12
            }
        );

        revealElements.forEach(function (element) {

            element.style.opacity = "0";

            element.style.transform = "translateY(18px)";

            element.style.transition =
                "opacity .6s ease, transform .6s ease";

            revealObserver.observe(element);

        });

    }


    /* =====================================================
       BUTTON FEEDBACK
       ===================================================== */

    const buttons = document.querySelectorAll(".btn");

    buttons.forEach(function (button) {

        button.addEventListener("mouseenter", function () {
            this.style.cursor = "pointer";
        });

    });


    /* =====================================================
       CURRENT YEAR
       ===================================================== */

    const yearElements =
        document.querySelectorAll("[data-year]");

    yearElements.forEach(function (element) {

        element.textContent = new Date().getFullYear();

    });

});
