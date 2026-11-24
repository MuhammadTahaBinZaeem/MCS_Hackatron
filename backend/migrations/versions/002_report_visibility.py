"""Add restricted-by-default report visibility and confidential linkage."""
from alembic import op

revision = '002_report_visibility'
down_revision = '001_domain'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE reports ADD COLUMN case_id VARCHAR(36) REFERENCES confidential_cases(id)")
    op.execute("ALTER TABLE reports ADD COLUMN visibility VARCHAR(40) NOT NULL DEFAULT 'RESTRICTED' CHECK (visibility IN ('PUBLIC', 'CONFIDENTIAL', 'RESTRICTED'))")

def downgrade():
    op.execute('ALTER TABLE reports DROP COLUMN visibility')
    op.execute('ALTER TABLE reports DROP COLUMN case_id')
