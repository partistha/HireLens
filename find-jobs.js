const API_URL = "http://127.0.0.1:5000";

const user = JSON.parse(localStorage.getItem("hirelens_user") || "null");

const jobList = document.getElementById("jobList");
const searchInput = document.getElementById("searchInput");
const categoryFilter = document.getElementById("categoryFilter");
const jobCount = document.getElementById("jobCount");

let allJobs = [];
let appliedIds = [];

if (!user || user.role !== "candidate") {
    alert("Please login as a candidate first.");
    window.location.href = "login.html";
}

async function loadJobs() {
    jobList.textContent = "Loading jobs...";

    try {
        const response = await fetch(`${API_URL}/api/jobs`);
        const result = await response.json();

        if (!response.ok) {
            throw new Error("Could not load jobs.");
        }

        allJobs = Array.isArray(result) ? result : (result.jobs || []);

        const appResponse = await fetch(
            `${API_URL}/api/candidate/${user.id}/applications`
        );

        if (appResponse.ok) {
            const appResult = await appResponse.json();
            const applications = Array.isArray(appResult)
                ? appResult
                : (appResult.applications || []);

            appliedIds = applications.map(item => String(item.job_id));
        }

        renderJobs();

    } catch (error) {
        console.error(error);
        jobList.textContent =
            "Unable to load jobs. Please check whether the backend is running.";
    }
}

function getCategory(job) {
    const text = (
        (job.title || "") + " " + (job.required_skills || "")
    ).toLowerCase();

    if (/cyber|security|network|linux/.test(text)) return "Security";
    if (/data|machine learning|pandas|analytics|sql/.test(text)) return "Data";
    if (/design|figma|ui|ux/.test(text)) return "Design";

    return "Development";
}

function renderJobs() {
    const query = searchInput.value.trim().toLowerCase();
    const category = categoryFilter.value;

    const filtered = allJobs.filter(job => {
        const searchable = [
            job.title,
            job.company,
            job.location,
            job.required_skills,
            job.description
        ].join(" ").toLowerCase();

        return searchable.includes(query) &&
            (category === "all" || getCategory(job) === category);
    });

    jobCount.textContent =
        `${filtered.length} ${filtered.length === 1 ? "opportunity" : "opportunities"}`;

    jobList.innerHTML = "";

    if (filtered.length === 0) {
        jobList.innerHTML =
            '<div class="empty-state">No matching jobs found.</div>';
        return;
    }

    filtered.forEach(job => {
        const card = document.createElement("article");
        card.className = "job-card";

        const title = document.createElement("h3");
        title.textContent = job.title || "Untitled Job";

        const company = document.createElement("div");
        company.className = "company-name";
        company.textContent = job.company || "Company";

        const meta = document.createElement("div");
        meta.className = "job-meta";
        meta.textContent =
            `${job.location || "Location not specified"} · ${getCategory(job)}`;

        const description = document.createElement("p");
        description.className = "job-description";
        description.textContent = job.description || "Explore this opportunity.";

        const skills = document.createElement("div");
        skills.className = "skill-tags";
        skills.textContent = "Skills: " + (job.required_skills || "Not specified");

        const button = document.createElement("button");
        button.className = "primary-btn apply-btn";

        const alreadyApplied = appliedIds.includes(String(job.id));

        button.textContent = alreadyApplied ? "✓ Applied" : "Apply Now ↗";
        button.disabled = alreadyApplied;
        button.dataset.jobId = job.id;

        if (alreadyApplied) button.classList.add("applied");

        card.append(title, company, meta, description, skills, button);
        jobList.appendChild(card);
    });
}

jobList.addEventListener("click", async function(event) {
    const button = event.target.closest("[data-job-id]");

    if (!button || button.disabled) return;

    const jobId = Number(button.dataset.jobId);

    button.disabled = true;
    button.textContent = "Applying...";

    try {
        const response = await fetch(`${API_URL}/api/applications`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                candidate_id: user.id,
                job_id: jobId
            })
        });

        const result = await response.json();

        if (!response.ok || result.success === false) {
            throw new Error(result.message || result.error || "Application failed.");
        }

        appliedIds.push(String(jobId));
        renderJobs();

        alert("Application submitted successfully!");

    } catch (error) {
        alert(error.message);
        button.disabled = false;
        button.textContent = "Apply Now ↗";
    }
});

document.getElementById("searchButton").addEventListener("click", renderJobs);
searchInput.addEventListener("input", renderJobs);
categoryFilter.addEventListener("change", renderJobs);

if (user && user.role === "candidate") {
    loadJobs();
}