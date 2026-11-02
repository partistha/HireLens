USE hirelens_db;


-- 1. Candidate Profile Table

CREATE TABLE IF NOT EXISTS candidate_profiles (

    id INT NOT NULL AUTO_INCREMENT,

    candidate_id INT NOT NULL,

    full_name VARCHAR(150),

    phone VARCHAR(30),

    education VARCHAR(255),

    location VARCHAR(150),

    skills TEXT,

    about TEXT,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_candidate_profile (candidate_id),

    CONSTRAINT fk_profile_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES users(id)
        ON DELETE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 2. Resume Table

CREATE TABLE IF NOT EXISTS resumes (

    id INT NOT NULL AUTO_INCREMENT,

    candidate_id INT NOT NULL,

    file_name VARCHAR(255) NOT NULL,

    file_path VARCHAR(500) NOT NULL,

    extracted_text LONGTEXT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_resume_candidate (candidate_id),

    CONSTRAINT fk_resume_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES users(id)
        ON DELETE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 3. Job Applications Table

CREATE TABLE IF NOT EXISTS applications (

    id INT NOT NULL AUTO_INCREMENT,

    job_id INT NOT NULL,

    candidate_id INT NOT NULL,

    match_score DECIMAL(5,2) DEFAULT 0,

    status ENUM(
        'Pending',
        'Shortlisted',
        'Interview',
        'Rejected',
        'Hired'
    ) NOT NULL DEFAULT 'Pending',

    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_candidate_job (candidate_id, job_id),

    KEY idx_application_job (job_id),

    KEY idx_application_candidate (candidate_id),

    CONSTRAINT fk_application_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_application_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES users(id)
        ON DELETE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;