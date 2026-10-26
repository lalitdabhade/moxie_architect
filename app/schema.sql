CREATE TABLE IF NOT EXISTS sections (
    id          TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    slug        VARCHAR(60)  NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    sort_order  TINYINT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admins (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_sessions (
    id          CHAR(64)     NOT NULL PRIMARY KEY,
    admin_id    INT UNSIGNED NOT NULL,
    csrf_token  CHAR(64)     NOT NULL,
    created_at  DATETIME     NOT NULL,
    expires_at  DATETIME     NOT NULL,
    INDEX idx_sessions_expires (expires_at),
    CONSTRAINT fk_sessions_admin FOREIGN KEY (admin_id) REFERENCES admins (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS projects (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    section_id  TINYINT UNSIGNED NOT NULL,
    title       VARCHAR(200) NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_projects_section (section_id, created_at),
    CONSTRAINT fk_projects_section FOREIGN KEY (section_id) REFERENCES sections (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS project_images (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id  INT UNSIGNED NOT NULL,
    path        VARCHAR(255) NOT NULL,
    sort_order  INT          NOT NULL DEFAULT 0,
    INDEX idx_images_project (project_id, sort_order),
    CONSTRAINT fk_images_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inquiries (
    id                    INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    mobile                CHAR(10)     NOT NULL,
    email                 VARCHAR(254) NOT NULL,
    address               VARCHAR(500) NOT NULL,
    service_type          ENUM('interior', 'bungalow_apartment') NOT NULL,
    house_type            ENUM('1bhk', '2bhk', '3bhk', 'bungalow', 'other') NULL,
    house_type_other      VARCHAR(100) NULL,
    area_sqft             INT UNSIGNED NULL,
    layout_file_path      VARCHAR(255) NULL,
    layout_original_name  VARCHAR(255) NULL,
    budget_range          ENUM('under_5l', '5_10l', '10_20l', '20_50l', 'above_50l') NOT NULL,
    created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_inquiries_created (created_at),
    INDEX idx_inquiries_service (service_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
