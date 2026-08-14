"""
Read-Only Database Schema Audit Script for Foundation PostgreSQL Database.
Strictly read-only: performs introspection using SQLAlchemy Inspector and pg_catalog.
Never modifies data or schema. Never prints credentials.
"""

import json
import sys
import os

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect, text
from app.core.database import engine, check_database_connection
from app.core.config import settings


def run_schema_audit() -> dict:
    # 1. Check basic connection
    conn_info = check_database_connection()
    if conn_info.get("status") != "connected":
        print(f"[AUDIT FAILED] Unable to connect: {conn_info.get('error')}", file=sys.stderr)
        return {"error": conn_info}

    print(f"[AUDIT] Connected successfully to database: {conn_info.get('database')} (PostgreSQL: {conn_info.get('version')})")

    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    target_schema = "public"

    audit_data = {
        "database_info": {
            "name": conn_info.get("database"),
            "version": conn_info.get("version"),
            "target": settings.safe_database_display,
        },
        "schemas": schemas,
        "tables": {},
        "enums": [],
    }

    # Inspect enum types if any in PostgreSQL
    with engine.connect() as connection:
        enum_result = connection.execute(text("""
            SELECT t.typname as enum_name,
                   array_agg(e.enumlabel ORDER BY e.enumsortorder) as enum_values
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public'
            GROUP BY t.typname;
        """))
        for row in enum_result.mappings():
            audit_data["enums"].append({
                "name": row["enum_name"],
                "values": list(row["enum_values"]) if row["enum_values"] else [],
            })

    # Inspect tables in public schema
    table_names = inspector.get_table_names(schema=target_schema)
    audit_data["table_list"] = table_names

    with engine.connect() as connection:
        for tbl in table_names:
            # Row count
            try:
                count_res = connection.execute(text(f'SELECT COUNT(*) FROM "{target_schema}"."{tbl}"'))
                row_count = count_res.scalar()
            except Exception as e:
                row_count = f"Error: {str(e)}"

            # Columns
            cols = inspector.get_columns(tbl, schema=target_schema)
            formatted_cols = []
            for col in cols:
                formatted_cols.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default")) if col.get("default") is not None else None,
                    "autoincrement": col.get("autoincrement", False),
                })

            # Primary Key
            pk = inspector.get_pk_constraint(tbl, schema=target_schema)

            # Foreign Keys
            fks = inspector.get_foreign_keys(tbl, schema=target_schema)
            formatted_fks = []
            for fk in fks:
                formatted_fks.append({
                    "name": fk.get("name"),
                    "constrained_columns": fk.get("constrained_columns"),
                    "referred_schema": fk.get("referred_schema"),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns"),
                    "options": fk.get("options", {}),
                })

            # Unique Constraints
            uniques = inspector.get_unique_constraints(tbl, schema=target_schema)

            # Indexes
            indexes = inspector.get_indexes(tbl, schema=target_schema)
            formatted_indexes = []
            for idx in indexes:
                formatted_indexes.append({
                    "name": idx.get("name"),
                    "column_names": idx.get("column_names"),
                    "unique": idx.get("unique", False),
                })

            audit_data["tables"][tbl] = {
                "row_count": row_count,
                "columns": formatted_cols,
                "primary_key": pk.get("constrained_columns", []),
                "foreign_keys": formatted_fks,
                "unique_constraints": uniques,
                "indexes": formatted_indexes,
            }

    return audit_data


if __name__ == "__main__":
    result = run_schema_audit()
    output_path = os.path.join(os.path.dirname(__file__), "schema_audit.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"[AUDIT COMPLETE] Results saved to {output_path}")
    print(f"[AUDIT SUMMARY] Found {len(result.get('table_list', []))} tables:")
    for t in result.get("table_list", []):
        tbl_info = result["tables"][t]
        print(f"  - {t}: {tbl_info['row_count']} rows, {len(tbl_info['columns'])} columns, {len(tbl_info['foreign_keys'])} FKs, {len(tbl_info['indexes'])} indexes")
