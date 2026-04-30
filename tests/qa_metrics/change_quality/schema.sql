-- cmk_change_tested: per-change record of "did this change include a test?"
--
-- v1 of the change-quality KPI populates rows where werk_class = 'fix' only.
-- Schema is intentionally cohort-agnostic so v2+ (feature, security, ...) can
-- extend the dataset with no DDL.

CREATE TABLE IF NOT EXISTS cmk_change_tested (
    werk_id          INTEGER NOT NULL,
    branch           VARCHAR NOT NULL,
    -- werk metadata
    werk_class       VARCHAR NOT NULL,
    werk_component   VARCHAR NOT NULL,
    werk_date        TIMESTAMP WITH TIME ZONE NOT NULL,
    edition          VARCHAR NOT NULL,
    level            SMALLINT NOT NULL,
    title            VARCHAR NOT NULL,
    -- commit metadata
    git_commit_hash  VARCHAR NOT NULL,
    commit_time      TIMESTAMP WITH TIME ZONE NOT NULL,
    author_email     VARCHAR,
    subject          VARCHAR,
    gerrit_change_id VARCHAR,
    -- derived
    source_component VARCHAR,
    has_test         BOOLEAN NOT NULL,
    files_changed    INTEGER NOT NULL,
    -- Provenance: set on first INSERT (DB DEFAULT). Not in the row dataclass,
    -- so ON CONFLICT DO UPDATE leaves it untouched -- it tracks "first seen",
    -- not "last refreshed".
    first_inserted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (werk_id, branch)
);

CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_date        ON cmk_change_tested(werk_date);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_class       ON cmk_change_tested(werk_class);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_component   ON cmk_change_tested(werk_component);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_source_component ON cmk_change_tested(source_component);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_branch           ON cmk_change_tested(branch);

COMMENT ON TABLE cmk_change_tested IS
  'Per-werk record of whether the introducing commit included a test file. '
  'PK (werk_id, branch) - cherry-picks produce one row per branch.';
