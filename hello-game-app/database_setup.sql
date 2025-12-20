-- Create the table
CREATE TABLE game_submissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Grant read permission to hello-backend-sa
GRANT SELECT ON game_submissions TO "hello-backend-sa@project_id_placeholder.iam";

-- Grant write permission to hello-function-sa (need INSERT and SEQUENCE usage)
GRANT INSERT ON game_submissions TO "hello-function-sa@project_id_placeholder.iam";
GRANT USAGE, SELECT ON SEQUENCE game_submissions_id_seq TO "hello-function-sa@project_id_placeholder.iam";