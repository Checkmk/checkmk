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
    -- has_test is NULL when the commit changed only .werks/<id> files: in that
    -- case the fix is in a separate commit and we have no signal. Treat NULL
    -- as "unknown", not as False, in any consumer queries.
    has_test         BOOLEAN,
    files_changed    INTEGER NOT NULL,
    -- Provenance: set on first INSERT (DB DEFAULT). Not in the row dataclass,
    -- so ON CONFLICT DO UPDATE leaves it untouched -- it tracks "first seen",
    -- not "last refreshed".
    first_inserted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (werk_id, branch)
);

-- Migration for deployments created before has_test became nullable: drop
-- the NOT NULL constraint idempotently. No-op on fresh tables.
ALTER TABLE cmk_change_tested ALTER COLUMN has_test DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_date        ON cmk_change_tested(werk_date);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_class       ON cmk_change_tested(werk_class);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_werk_component   ON cmk_change_tested(werk_component);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_source_component ON cmk_change_tested(source_component);
CREATE INDEX IF NOT EXISTS idx_cmk_change_tested_branch           ON cmk_change_tested(branch);

COMMENT ON TABLE cmk_change_tested IS
  'Per-werk record of whether the change included a test file. '
  'has_test=NULL means no signal (werk added in a separate commit from the fix). '
  'PK (werk_id, branch) - cherry-picks produce one row per branch.';
