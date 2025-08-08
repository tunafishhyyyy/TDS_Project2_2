"""
DuckDB query execution tools
"""
import duckdb
import pandas as pd
from typing import Dict, Any, List, Optional
import json
import tempfile
import os
from app.logger import logger


class DuckDBRunner:
    """DuckDB query execution and data management"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or ":memory:"
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Connect to DuckDB"""
        try:
            self.connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to DuckDB: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {str(e)}")
            raise
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        try:
            logger.info(f"Executing query: {query[:100]}...")
            
            result = self.connection.execute(query).fetchall()
            columns = [desc[0] for desc in self.connection.description]
            
            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]
            
            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "rows": len(data),
                    "columns": columns,
                    "query": query
                }
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "data": None,
                "metadata": {"query": query}
            }
    
    def load_dataframe(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Load pandas DataFrame into DuckDB table"""
        try:
            self.connection.register(table_name, df)
            logger.info(f"Loaded DataFrame as table: {table_name}")
            
            return {
                "status": "success",
                "table_name": table_name,
                "rows": len(df),
                "columns": df.columns.tolist()
            }
            
        except Exception as e:
            logger.error(f"Failed to load DataFrame: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def load_from_dict(self, data: List[Dict], table_name: str) -> Dict[str, Any]:
        """Load dictionary data into DuckDB table"""
        try:
            df = pd.DataFrame(data)
            return self.load_dataframe(df, table_name)
            
        except Exception as e:
            logger.error(f"Failed to load dict data: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def list_tables(self) -> Dict[str, Any]:
        """List all tables in the database"""
        try:
            result = self.connection.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in result]
            
            return {
                "status": "success",
                "tables": tables
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e), "tables": []}
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information"""
        try:
            query = f"DESCRIBE {table_name}"
            result = self.connection.execute(query).fetchall()
            
            schema = []
            for row in result:
                schema.append({
                    "column_name": row[0],
                    "column_type": row[1],
                    "null": row[2],
                    "key": row[3] if len(row) > 3 else None,
                    "default": row[4] if len(row) > 4 else None
                })
            
            return {
                "status": "success",
                "table_name": table_name,
                "schema": schema
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("DuckDB connection closed")


# Global DuckDB instance
_db_runner = None


def get_duckdb_runner() -> DuckDBRunner:
    """Get or create global DuckDB runner instance"""
    global _db_runner
    if _db_runner is None:
        _db_runner = DuckDBRunner()
    return _db_runner


def duckdb_runner(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute DuckDB operations
    
    Args:
        params: {
            "operation": str - "query", "load_data", "list_tables", "describe"
            "query": str - SQL query (for query operation)
            "data": list/dict - data to load (for load_data operation)
            "table_name": str - table name
            "source_format": str - "json", "csv_data", etc.
        }
    """
    try:
        db = get_duckdb_runner()
        
        operation = params.get("operation", "query")
        
        if operation == "query":
            query = params.get("query")
            if not query:
                raise ValueError("query parameter is required")
            return db.execute_query(query)
        
        elif operation == "load_data":
            data = params.get("data")
            table_name = params.get("table_name")
            source_format = params.get("source_format", "json")
            
            if not data or not table_name:
                raise ValueError("data and table_name are required")
            
            if isinstance(data, list):
                return db.load_from_dict(data, table_name)
            elif isinstance(data, pd.DataFrame):
                return db.load_dataframe(data, table_name)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
        
        elif operation == "list_tables":
            return db.list_tables()
        
        elif operation == "describe":
            table_name = params.get("table_name")
            if not table_name:
                raise ValueError("table_name is required")
            return db.describe_table(table_name)
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    except Exception as e:
        logger.error(f"DuckDB operation failed: {str(e)}")
        return {"status": "error", "error": str(e), "data": None}
