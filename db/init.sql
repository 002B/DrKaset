-- DrKaset — initial schema
-- รันครั้งเดียวก่อนเริ่ม backend
-- mysql -u root -p < db/init.sql

CREATE DATABASE IF NOT EXISTS drkaset_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'drkaset_user'@'localhost' IDENTIFIED BY 'drkaset_pass';
GRANT ALL PRIVILEGES ON drkaset_db.* TO 'drkaset_user'@'localhost';
FLUSH PRIVILEGES;

USE drkaset_db;

-- ── Users ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    email            VARCHAR(255) NOT NULL UNIQUE,
    hashed_password  VARCHAR(255) NOT NULL,
    is_active        TINYINT(1)   NOT NULL DEFAULT 1,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Chat Sessions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    title       VARCHAR(255),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sessions_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Chat Messages ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    session_id  INT          NOT NULL,
    role        ENUM('user','assistant') NOT NULL,
    content     TEXT         NOT NULL,
    intent      VARCHAR(50),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_messages_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Ingestion Logs ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    file_name      VARCHAR(255) NOT NULL,
    file_type      VARCHAR(50),
    record_count   INT          NOT NULL DEFAULT 0,
    status         ENUM('pending','processing','done','error') NOT NULL DEFAULT 'pending',
    error_message  TEXT,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at    DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
