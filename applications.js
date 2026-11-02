
document.addEventListener("DOMContentLoaded", async function () {
    const API_URL = "http://127.0.0.1:5000";

    let user = null;

    try {
        user = JSON.parse(localStorage.getItem("hirelens_user") || "null");
    } catch (error) {
        user = null;
    }

    const list = document.getElementById("applicationList");
    const searchInput = document.getElementById("applicationSearch");
    const statusFilter = document.getElementById("statusFilter");
    const filters = document.getElementById("filters");

    let applications = [];
    let currentFilter = "all";
    let searchText = "";

    if (!user || user.role !== "candidate" || !user.id) {
        alert("Please login as a candidate first.");
        window.location.href = "login.html";
        return;
    }

    document.querySelectorAll("[data-user-name]").forEach(el => {
        el.textContent = user.name || "Candidate";
    });

    document.querySelectorAll("[data-user-initial]").forEach(el => {
        el.textContent = (user.name || "C").charAt(0).toUpperCase();
    });

    function statusOf(app) {
        const status = String(
            app.application_status || app.status || "pending"
        ).toLowerCase();

        if (status === "under review" || status === "in review") {
            return "review";
        }

        if (["pending", "shortlisted", "rejected", "interview", "hired"].includes(status)) {
            return status;
        }

        return "pending";
    }

    function createElement(tag, className, value) {
        const node = document.createElement(tag);

        if (className) node.className = className;
        if (value !== undefined) node.textContent = value;

        return node;
    }

    function render() {
        document.getElementById("totalCount").textContent = applications.length;

        document.getElementById("pendingCount").textContent =
            applications.filter(a => statusOf(a) === "pending").length;

        document.getElementById("shortlistedCount").textContent =
            applications.filter(a => statusOf(a) === "shortlisted").length;

        document.getElementById("reviewCount").textContent =
            applications.filter(a =>
                ["review", "interview"].includes(statusOf(a))
            ).length;

        list.replaceChildren();

        const rows = applications.filter(app => {
            const status = statusOf(app);

            const matchesStatus =
                currentFilter === "all" || status === currentFilter;

            const text =
                `${app.title || ""} ${app.company || ""}`.toLowerCase();

            return matchesStatus && text.includes(searchText);
        });

        if (rows.length === 0) {
            const empty = createElement("div", "empty-state");

            empty.append(
                createElement("div", "empty-icon", "▤"),
                createElement(
                    "h3",
                    "",
                    applications.length
                        ? "No matching applications"
                        : "No applications yet"
                ),
                createElement(
                    "p",
                    "",
                    applications.length
                        ? "Try another search or filter."
                        : "Upload your resume in My Profile, then explore jobs and apply."
                )
            );

            const link = createElement("a", "", "Explore Jobs →");
            link.href = "find-jobs.html";

            empty.append(link);
            list.append(empty);
            return;
        }

        rows.forEach(app => {
            const card = createElement("article", "application-card");
            const details = createElement("div", "job-details");
            const heading = createElement("div", "job-heading");

            heading.append(
                createElement("h3", "", app.title || "Untitled Position")
            );

            details.append(
                heading,
                createElement(
                    "div",
                    "company-name",
                    app.company || "Company not specified"
                ),
                createElement(
                    "div",
                    "job-meta",
                    `📍 ${app.location || "Location not specified"} · Applied ${
                        app.applied_at
                            ? new Date(app.applied_at).toLocaleDateString()
                            : "recently"
                    }`
                )
            );

            const right = createElement("div", "job-right");
            const status = statusOf(app);

            right.append(
                createElement(
                    "span",
                    `status-badge ${status}`,
                    status.charAt(0).toUpperCase() + status.slice(1)
                )
            );

            const actions = createElement("div", "job-actions");
            const explore = createElement("a", "job-button", "Explore Jobs");

            explore.href = "find-jobs.html";
            actions.append(explore);
            right.append(actions);

            card.append(details, right);
            list.append(card);
        });
    }

    async function loadApplications() {
        list.textContent = "Loading your applications...";

        try {
            const response = await fetch(
                `${API_URL}/api/candidate/${user.id}/applications`
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(
                    data.message || "Could not load applications."
                );
            }

            applications = data.applications || [];
            render();

        } catch (error) {
            list.textContent =
                `${error.message} Please make sure the HireLens backend is running.`;
        }
    }

    filters.addEventListener("click", function (event) {
        const button = event.target.closest("[data-filter]");

        if (!button) return;

        currentFilter = button.dataset.filter;

        document.querySelectorAll(".filter-tab").forEach(tab => {
            tab.classList.toggle("active", tab === button);
        });

        statusFilter.value = currentFilter;
        render();
    });

    searchInput.addEventListener("input", function () {
        searchText = searchInput.value.trim().toLowerCase();
        render();
    });

    statusFilter.addEventListener("change", function () {
        currentFilter = statusFilter.value;

        document.querySelectorAll(".filter-tab").forEach(tab => {
            tab.classList.toggle(
                "active",
                tab.dataset.filter === currentFilter
            );
        });

        render();
    });

    await loadApplications();
});
