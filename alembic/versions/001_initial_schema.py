"""Initial schema for dynamic core licensing.

Revision ID: 001_initial
Revises: None
Create Date: 2026-09-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entitlements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product", sa.String(100), nullable=False),
        sa.Column("edition", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("license_type", sa.String(30), nullable=False),
        sa.Column("core_quantity", sa.Integer(), nullable=False),
        sa.Column("agreement_ref", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "vms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hostname", sa.String(255), nullable=False, index=True),
        sa.Column("hypervisor_uuid", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("core_count", sa.Integer(), nullable=False),
        sa.Column("server_farm", sa.String(100), nullable=False),
        sa.Column("current_state", sa.String(30), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("activation_status", sa.String(100), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconciled", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "leases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entitlement_id", sa.Integer(), sa.ForeignKey("entitlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vm_id", sa.Integer(), sa.ForeignKey("vms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("cores_allocated", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(255), nullable=True),
    )
    op.create_index("ix_leases_vm_status", "leases", ["vm_id", "status"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("vm_id", sa.Integer(), sa.ForeignKey("vms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("ix_leases_vm_status", table_name="leases")
    op.drop_table("leases")
    op.drop_table("vms")
    op.drop_table("entitlements")
