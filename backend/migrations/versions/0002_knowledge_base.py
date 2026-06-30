"""knowledge base ingestion

Revision ID: 0002_knowledge_base
Revises: 0001_backend_initial
Create Date: 2026-06-30 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0002_knowledge_base"
down_revision: Union[str, None] = "0001_backend_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_schema() -> str:
    return context.config.get_main_option("backend_schema") or "backend"


def upgrade() -> None:
    schema = _get_schema()
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=schema,
    )
    op.create_index(
        "ix_knowledge_documents_created_by",
        "knowledge_documents",
        ["created_by"],
        schema=schema,
    )
    op.create_table(
        "knowledge_document_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("chroma_collection", sa.String(255), nullable=False),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            [f"{schema}.knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "version",
            name="uq_knowledge_document_version",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_knowledge_document_versions_document_id",
        "knowledge_document_versions",
        ["document_id"],
        schema=schema,
    )
    op.create_table(
        "knowledge_chunk_metadata",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_version_id", sa.String(36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chroma_id", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            [f"{schema}.knowledge_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chroma_id"),
        sa.UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_knowledge_chunk_index",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_knowledge_chunk_metadata_document_version_id",
        "knowledge_chunk_metadata",
        ["document_version_id"],
        schema=schema,
    )


def downgrade() -> None:
    schema = _get_schema()
    op.drop_index(
        "ix_knowledge_chunk_metadata_document_version_id",
        table_name="knowledge_chunk_metadata",
        schema=schema,
    )
    op.drop_table("knowledge_chunk_metadata", schema=schema)
    op.drop_index(
        "ix_knowledge_document_versions_document_id",
        table_name="knowledge_document_versions",
        schema=schema,
    )
    op.drop_table("knowledge_document_versions", schema=schema)
    op.drop_index(
        "ix_knowledge_documents_created_by",
        table_name="knowledge_documents",
        schema=schema,
    )
    op.drop_table("knowledge_documents", schema=schema)
