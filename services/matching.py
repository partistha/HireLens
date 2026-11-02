
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILL_LIST = [
    "python",
    "java",
    "javascript",
    "html",
    "css",
    "react",
    "angular",
    "node.js",
    "flask",
    "django",
    "sql",
    "mysql",
    "mongodb",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data science",
    "data analysis",
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "tensorflow",
    "pytorch",
    "nlp",
    "excel",
    "power bi",
    "tableau",
    "aws",
    "azure",
    "docker",
    "git",
    "cybersecurity",
    "networking",
    "linux",
    "c",
    "c++",
    "problem solving"
]


def normalize_text(text):
    text = str(text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_skills(text):
    text = normalize_text(text)

    found = []

    for skill in SKILL_LIST:
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(skill.lower())
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, text):
            found.append(skill)

    return sorted(set(found))


def get_required_skills(job):
    raw_skills = job.get("required_skills") or ""

    if isinstance(raw_skills, list):
        raw_skills = " ".join(map(str, raw_skills))

    raw_skills = normalize_text(raw_skills)

    required = extract_skills(raw_skills)

    # Preserve additional manually specified skill names
    if not required and raw_skills:
        required = [
            item.strip()
            for item in re.split(r"[,;\n]", raw_skills)
            if item.strip()
        ]

    return sorted(set(required))


def calculate_match(candidate_text, job):
    """
    Returns:
    score, matched_skills, missing_skills
    """

    candidate_text = normalize_text(candidate_text)

    job_title = normalize_text(job.get("title", ""))
    description = normalize_text(job.get("description", ""))

    required_skills = get_required_skills(job)
    candidate_skills = extract_skills(candidate_text)

    matched_skills = [
        skill for skill in required_skills
        if skill.lower() in candidate_skills
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill.lower() not in candidate_skills
    ]

    if required_skills:
        skill_score = (
            len(matched_skills) / len(required_skills)
        ) * 100
    else:
        skill_score = 0

    job_text = " ".join([
        job_title,
        description,
        " ".join(required_skills)
    ]).strip()

    text_score = 0

    if candidate_text and job_text:
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=5000
            )

            matrix = vectorizer.fit_transform([
                candidate_text,
                job_text
            ])

            text_score = (
                cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
                * 100
            )

        except ValueError:
            text_score = 0

    if required_skills:
        final_score = (
            skill_score * 0.70
            + text_score * 0.30
        )
    else:
        final_score = text_score

    final_score = round(
        max(0, min(100, final_score)), 2
    )

    return (
        final_score,
        matched_skills,
        missing_skills
    )
