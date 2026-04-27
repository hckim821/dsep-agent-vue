-- Seed: admin user (email: admin@llmwiki.local, password: admin1234)
-- bcrypt hash generated via passlib bcrypt scheme.
INSERT INTO users (email, password_hash, display_name, role)
VALUES (
  'admin@llmwiki.local',
  '$2b$12$choJgSNoN.gyNDBPM6D2s.LVlXJXEsdGsCld8Py4e6zlzqymjY9RO',
  'Admin',
  'admin'
)
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);

-- Seed: initial schema_versions row referencing the admin user.
INSERT INTO schema_versions (content, updated_by, note)
SELECT
  '# LLM Wiki Schema (initial)\n\n도메인 스키마 초기 버전입니다. /admin/schema 에서 편집 가능.\n',
  u.id,
  'Initial schema'
FROM users u
WHERE u.email = 'admin@llmwiki.local'
  AND NOT EXISTS (SELECT 1 FROM schema_versions);
