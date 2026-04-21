USE drkaset_db;

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
