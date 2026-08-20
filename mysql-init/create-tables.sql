-- mysql-init/init.sql
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(20) NOT NULL,
    status VARCHAR(6) NOT NULL,
    time_status DATE NULL,
    requests INT NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;