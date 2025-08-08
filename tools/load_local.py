"""
Local file loading tools
"""
import pandas as pd
import json
import csv
from typing import Dict, Any, List
import os
from pathlib import Path
from app.logger import logger


def load_local(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load local files (CSV, JSON, Excel, etc.)
    
    Args:
        params: {
            "file_path": str - path to file
            "file_type": str - "csv", "json", "excel", "txt"
            "encoding": str - file encoding
            "options": dict - additional pandas/json options
        }
    """
    try:
        file_path = params.get("file_path")
        file_type = params.get("file_type", "auto")
        encoding = params.get("encoding", "utf-8")
        options = params.get("options", {})
        
        if not file_path:
            raise ValueError("file_path is required")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Loading local file: {file_path}")
        
        # Auto-detect file type from extension
        if file_type == "auto":
            file_type = Path(file_path).suffix.lower().lstrip(".")
        
        # Load based on file type
        if file_type in ["csv"]:
            return _load_csv(file_path, encoding, options)
        elif file_type in ["json", "jsonl"]:
            return _load_json(file_path, encoding, options)
        elif file_type in ["xlsx", "xls", "excel"]:
            return _load_excel(file_path, options)
        elif file_type in ["txt", "text"]:
            return _load_text(file_path, encoding)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        logger.error(f"Failed to load file: {str(e)}")
        return {"error": str(e), "data": None}


def _load_csv(file_path: str, encoding: str, options: Dict) -> Dict[str, Any]:
    """Load CSV file"""
    try:
        df = pd.read_csv(file_path, encoding=encoding, **options)
        
        return {
            "file_path": file_path,
            "file_type": "csv",
            "status": "success",
            "data": df.to_dict("records"),
            "metadata": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict()
            }
        }
        
    except Exception as e:
        return {"error": str(e), "file_path": file_path, "data": None}


def _load_json(file_path: str, encoding: str, options: Dict) -> Dict[str, Any]:
    """Load JSON file"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            if file_path.endswith('.jsonl'):
                # JSON Lines format
                data = [json.loads(line) for line in f]
            else:
                # Regular JSON
                data = json.load(f)
        
        return {
            "file_path": file_path,
            "file_type": "json",
            "status": "success", 
            "data": data,
            "metadata": {
                "size": len(data) if isinstance(data, list) else 1,
                "type": type(data).__name__
            }
        }
        
    except Exception as e:
        return {"error": str(e), "file_path": file_path, "data": None}


def _load_excel(file_path: str, options: Dict) -> Dict[str, Any]:
    """Load Excel file"""
    try:
        # Load all sheets by default
        sheet_name = options.get("sheet_name")
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name, **options)
            data = df.to_dict("records")
            metadata = {
                "sheet": sheet_name,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            }
        else:
            # Load all sheets
            dfs = pd.read_excel(file_path, sheet_name=None, **options)
            data = {sheet: df.to_dict("records") 
                   for sheet, df in dfs.items()}
            metadata = {
                "sheets": list(dfs.keys()),
                "sheet_info": {
                    sheet: {
                        "rows": len(df),
                        "columns": len(df.columns)
                    } for sheet, df in dfs.items()
                }
            }
        
        return {
            "file_path": file_path,
            "file_type": "excel",
            "status": "success",
            "data": data,
            "metadata": metadata
        }
        
    except Exception as e:
        return {"error": str(e), "file_path": file_path, "data": None}


def _load_text(file_path: str, encoding: str) -> Dict[str, Any]:
    """Load text file"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {
            "file_path": file_path,
            "file_type": "text",
            "status": "success",
            "data": content,
            "metadata": {
                "size_chars": len(content),
                "size_lines": len(content.split('\n'))
            }
        }
        
    except Exception as e:
        return {"error": str(e), "file_path": file_path, "data": None}
