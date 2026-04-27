"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-26
"""
from alembic import op


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def _supports_ngram_parser(bind) -> bool:
    """MySQL 5.7+ ships built-in ngram parser; MariaDB does not."""
    version = bind.exec_driver_sql("SELECT VERSION()").scalar() or ""
    return "MariaDB" not in version


def upgrade() -> None:
    bind = op.get_bind()
    ngram_clause = " WITH PARSER ngram" if _supports_ngram_parser(bind) else ""

    op.execute("""
        CREATE TABLE users (
          id BIGINT NOT NULL AUTO_INCREMENT,
          email VARCHAR(255) NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          display_name VARCHAR(100) NOT NULL,
          role ENUM('admin','editor','viewer') NOT NULL DEFAULT 'editor',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_users_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute(f"""
        CREATE TABLE ingest_posts (
          id BIGINT NOT NULL AUTO_INCREMENT,
          author_id BIGINT NOT NULL,
          title VARCHAR(500) NOT NULL,
          body_md MEDIUMTEXT NOT NULL,
          type ENUM('new','correction','chat_summary') NOT NULL DEFAULT 'new',
          priority ENUM('normal','urgent') NOT NULL DEFAULT 'normal',
          category VARCHAR(100) NULL,
          status ENUM('pending','ocr_running','ocr_done','ingest_running','ingest_done','done','failed') NOT NULL DEFAULT 'pending',
          source_url VARCHAR(1000) NULL,
          source_author VARCHAR(255) NULL,
          source_date DATE NULL,
          target_wiki_path VARCHAR(500) NULL,
          target_section_anchor VARCHAR(255) NULL,
          unverified BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_ingest_posts_status (status),
          KEY idx_ingest_posts_author (author_id),
          KEY idx_ingest_posts_category (category),
          KEY idx_ingest_posts_created (created_at),
          CONSTRAINT fk_ingest_posts_author FOREIGN KEY (author_id) REFERENCES users(id),
          FULLTEXT KEY ft_ingest_posts_title_body (title, body_md){ngram_clause}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE ingest_attachments (
          id BIGINT NOT NULL AUTO_INCREMENT,
          post_id BIGINT NOT NULL,
          stored_filename VARCHAR(500) NOT NULL,
          original_filename VARCHAR(500) NOT NULL,
          file_path VARCHAR(1000) NOT NULL,
          mime_type VARCHAR(100) NULL,
          size_bytes BIGINT NULL,
          ocr_text MEDIUMTEXT NULL,
          ocr_model VARCHAR(100) NULL,
          ocr_done_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_ingest_attachments_post (post_id),
          CONSTRAINT fk_ingest_attachments_post FOREIGN KEY (post_id) REFERENCES ingest_posts(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE ingest_jobs (
          id BIGINT NOT NULL AUTO_INCREMENT,
          post_id BIGINT NOT NULL,
          stage ENUM('ocr','ingest','lint') NOT NULL,
          status ENUM('running','success','failed') NOT NULL,
          started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          finished_at TIMESTAMP NULL,
          tokens_used INT NULL,
          model_used VARCHAR(100) NULL,
          log_text MEDIUMTEXT NULL,
          error_text TEXT NULL,
          PRIMARY KEY (id),
          KEY idx_ingest_jobs_post (post_id),
          KEY idx_ingest_jobs_started (started_at),
          CONSTRAINT fk_ingest_jobs_post FOREIGN KEY (post_id) REFERENCES ingest_posts(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute(f"""
        CREATE TABLE wiki_pages (
          id BIGINT NOT NULL AUTO_INCREMENT,
          path VARCHAR(500) NOT NULL,
          title VARCHAR(500) NOT NULL,
          category VARCHAR(100) NULL,
          current_commit_sha VARCHAR(40) NULL,
          last_ingest_id BIGINT NULL,
          summary TEXT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_wiki_pages_path (path),
          KEY idx_wiki_pages_category (category),
          FULLTEXT KEY ft_wiki_pages_title_summary (title, summary){ngram_clause}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE wiki_page_sources (
          id BIGINT NOT NULL AUTO_INCREMENT,
          wiki_page_id BIGINT NOT NULL,
          ingest_post_id BIGINT NOT NULL,
          relation ENUM('created','updated') NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_wps_page (wiki_page_id),
          KEY idx_wps_post (ingest_post_id),
          CONSTRAINT fk_wps_page FOREIGN KEY (wiki_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
          CONSTRAINT fk_wps_post FOREIGN KEY (ingest_post_id) REFERENCES ingest_posts(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE wiki_backlinks (
          from_page_id BIGINT NOT NULL,
          to_page_id BIGINT NOT NULL,
          PRIMARY KEY (from_page_id, to_page_id),
          KEY idx_wbl_to (to_page_id),
          CONSTRAINT fk_wbl_from FOREIGN KEY (from_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
          CONSTRAINT fk_wbl_to FOREIGN KEY (to_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE chat_sessions (
          id BIGINT NOT NULL AUTO_INCREMENT,
          user_id BIGINT NOT NULL,
          title VARCHAR(500) NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_chat_sessions_user (user_id),
          CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE chat_messages (
          id BIGINT NOT NULL AUTO_INCREMENT,
          session_id BIGINT NOT NULL,
          role ENUM('user','assistant','system') NOT NULL,
          content MEDIUMTEXT NOT NULL,
          citations_json JSON NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_chat_messages_session_created (session_id, created_at),
          CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE lint_findings (
          id BIGINT NOT NULL AUTO_INCREMENT,
          type ENUM('contradiction','orphan','stale','missing_entity','broken_link') NOT NULL,
          page_ids_json JSON NULL,
          description TEXT NULL,
          severity ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
          detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          resolved_at TIMESTAMP NULL,
          resolved_by_post_id BIGINT NULL,
          PRIMARY KEY (id),
          KEY idx_lint_findings_type_resolved (type, resolved_at),
          KEY idx_lint_findings_severity (severity),
          CONSTRAINT fk_lint_findings_post FOREIGN KEY (resolved_by_post_id) REFERENCES ingest_posts(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    op.execute("""
        CREATE TABLE schema_versions (
          id BIGINT NOT NULL AUTO_INCREMENT,
          content MEDIUMTEXT NOT NULL,
          updated_by BIGINT NOT NULL,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          note VARCHAR(500) NULL,
          PRIMARY KEY (id),
          KEY idx_schema_versions_updated (updated_at),
          CONSTRAINT fk_schema_versions_user FOREIGN KEY (updated_by) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)


def downgrade() -> None:
    for table in [
        "schema_versions",
        "lint_findings",
        "chat_messages",
        "chat_sessions",
        "wiki_backlinks",
        "wiki_page_sources",
        "wiki_pages",
        "ingest_jobs",
        "ingest_attachments",
        "ingest_posts",
        "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table}")
