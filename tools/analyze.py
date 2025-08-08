"""
Data analysis and statistical tools
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json
from app.logger import logger


def analyze(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform statistical analysis and data transformations
    
    Args:
        params: {
            "operation": str - "summary", "correlation", "groupby", "filter", "transform"
            "data": list/dict - input data
            "columns": list - columns to analyze
            "group_by": str/list - grouping columns
            "aggregations": dict - aggregation functions
            "filters": dict - filtering conditions
            "transform_type": str - transformation type
        }
    """
    try:
        data = params.get("data")
        operation = params.get("operation", "summary")
        
        if not data:
            raise ValueError("data parameter is required")
        
        # Convert data to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, dict):
            # Handle fetch_web output format
            if "data" in data and "tables" in data["data"]:
                # Extract table data from fetch_web output
                tables = data["data"]["tables"]
                if tables and len(tables) > 0:
                    # Use the first table by default
                    table_data = tables[0]
                    if "rows" in table_data:
                        df = pd.DataFrame(table_data["rows"])
                        # Set column names if available
                        if "columns" in table_data and df.shape[1] == len(table_data["columns"]):
                            df.columns = table_data["columns"]
                    else:
                        raise ValueError("Table data missing 'rows' field")
                else:
                    raise ValueError("No tables found in data")
            else:
                # Try to convert dict directly to DataFrame
                try:
                    df = pd.DataFrame(data)
                except Exception as e:
                    raise ValueError(f"Cannot convert dict to DataFrame: {data}")
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        logger.info(f"Performing analysis: {operation} on {len(df)} rows")
        
        if operation == "summary":
            return _generate_summary(df, params)
        elif operation == "correlation":
            return _calculate_correlation(df, params)
        elif operation == "groupby":
            return _perform_groupby(df, params)
        elif operation == "filter":
            return _filter_data(df, params)
        elif operation == "transform":
            return _transform_data(df, params)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return {"status": "error", "error": str(e), "data": None}


def _generate_summary(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate statistical summary"""
    try:
        columns = params.get("columns", df.columns.tolist())
        
        # Basic statistics
        summary_stats = df[columns].describe().to_dict()
        
        # Additional statistics
        additional_stats = {}
        for col in columns:
            if col in df.columns:
                series = df[col]
                additional_stats[col] = {
                    "null_count": series.isnull().sum(),
                    "null_percentage": (series.isnull().sum() / len(series)) * 100,
                    "unique_count": series.nunique(),
                    "dtype": str(series.dtype)
                }
                
                # For numeric columns
                if pd.api.types.is_numeric_dtype(series):
                    additional_stats[col].update({
                        "skewness": series.skew(),
                        "kurtosis": series.kurtosis()
                    })
        
        return {
            "status": "success",
            "data": {
                "basic_stats": summary_stats,
                "additional_stats": additional_stats,
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "column_types": df.dtypes.to_dict()
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _calculate_correlation(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate correlation matrix"""
    try:
        columns = params.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())
        method = params.get("method", "pearson")
        
        if not columns:
            raise ValueError("No numeric columns found for correlation")
        
        corr_matrix = df[columns].corr(method=method)
        
        return {
            "status": "success",
            "data": {
                "correlation_matrix": corr_matrix.to_dict(),
                "method": method,
                "columns": columns
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _perform_groupby(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform group by operations"""
    try:
        group_by = params.get("group_by")
        aggregations = params.get("aggregations", {"count": "size"})
        
        if not group_by:
            raise ValueError("group_by parameter is required")
        
        # Perform groupby
        grouped = df.groupby(group_by)
        
        results = {}
        for agg_name, agg_func in aggregations.items():
            if agg_func == "size":
                results[agg_name] = grouped.size().to_dict()
            elif agg_func in ["mean", "sum", "min", "max", "std", "count"]:
                results[agg_name] = getattr(grouped, agg_func)().to_dict()
            else:
                # Custom aggregation
                try:
                    results[agg_name] = grouped.agg(agg_func).to_dict()
                except Exception as e:
                    logger.warning(f"Custom aggregation failed: {str(e)}")
        
        return {
            "status": "success",
            "data": {
                "grouped_results": results,
                "group_by": group_by,
                "aggregations": aggregations
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _filter_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Filter data based on conditions"""
    try:
        filters = params.get("filters", {})
        
        filtered_df = df.copy()
        
        for column, condition in filters.items():
            if column not in df.columns:
                logger.warning(f"Column {column} not found, skipping filter")
                continue
            
            if isinstance(condition, dict):
                # Complex conditions
                if "gt" in condition:
                    filtered_df = filtered_df[filtered_df[column] > condition["gt"]]
                if "lt" in condition:
                    filtered_df = filtered_df[filtered_df[column] < condition["lt"]]
                if "eq" in condition:
                    filtered_df = filtered_df[filtered_df[column] == condition["eq"]]
                if "in" in condition:
                    filtered_df = filtered_df[filtered_df[column].isin(condition["in"])]
                if "contains" in condition:
                    filtered_df = filtered_df[filtered_df[column].str.contains(condition["contains"], na=False)]
            else:
                # Simple equality
                filtered_df = filtered_df[filtered_df[column] == condition]
        
        return {
            "status": "success",
            "data": filtered_df.to_dict("records"),
            "metadata": {
                "original_rows": len(df),
                "filtered_rows": len(filtered_df),
                "filters_applied": filters
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _transform_data(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Transform data"""
    try:
        transform_type = params.get("transform_type")
        columns = params.get("columns", df.columns.tolist())
        
        transformed_df = df.copy()
        
        if transform_type == "normalize":
            # Min-max normalization
            for col in columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if max_val != min_val:
                        transformed_df[col] = (df[col] - min_val) / (max_val - min_val)
        
        elif transform_type == "standardize":
            # Z-score standardization
            for col in columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    transformed_df[col] = (df[col] - df[col].mean()) / df[col].std()
        
        elif transform_type == "log":
            # Log transformation
            for col in columns:
                if pd.api.types.is_numeric_dtype(df[col]) and (df[col] > 0).all():
                    transformed_df[col] = np.log(df[col])
        
        else:
            raise ValueError(f"Unknown transform_type: {transform_type}")
        
        return {
            "status": "success",
            "data": transformed_df.to_dict("records"),
            "metadata": {
                "transform_type": transform_type,
                "columns_transformed": columns,
                "original_shape": df.shape,
                "transformed_shape": transformed_df.shape
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
