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
        # Accept 'input' as alias for 'data' for fallback plans
        if data is None and "input" in params:
            data = params["input"]
        if not data:
            return {"status": "error", "error": "data parameter is required or missing from previous step", "data": None}
        
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
                    if 'data' in data:
                        try:
                            df = pd.DataFrame(data['data'])
                        except Exception as e:
                            logger.error(f"Cannot convert input['data'] to DataFrame: {data['data']}")
                            raise
                    else:
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
        elif operation == "cleaning":
            cleaning = params.get("cleaning", {})
            cleaned_df = df.copy()
            for col, rule in cleaning.items():
                if col in cleaned_df.columns:
                    if "remove non-numeric" in rule:
                        cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r"[^\d.]", "", regex=True)
                    if "convert to float" in rule:
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce")
                    if "convert to int" in rule:
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce").astype('Int64')
            return {"status": "success", "data": cleaned_df.to_dict("records"), "columns": list(cleaned_df.columns)}
        elif operation == "generate_sql":
            # Generate SQL queries based on user questions and data schema
            from app.llm_client import llm_client
            
            # Get schema from the data
            schema_info = {
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict(),
                "sample_rows": df.head(5).to_dict("records")
            }
            
            user_query = params.get("query", "")
            context = params.get("context", {})
            
            # Extract table reference from context if available
            table_ref = "data"  # default
            if context:
                context_str = json.dumps(context)
                # Look for read_parquet or table patterns
                import re
                parquet_match = re.search(
                    r"read_parquet\(['\"]([^'\"]+)['\"]", context_str
                )
                if parquet_match:
                    table_ref = f"read_parquet('{parquet_match.group(1)}')"
            
            prompt = (
                "You are a SQL expert. Given the user questions and table "
                "schema, generate the specific SQL queries needed to answer "
                "each question.\n\n"
                f"Table Reference: {table_ref}\n"
                f"Schema: {json.dumps(schema_info, indent=2)}\n\n"
                f"User Questions: {user_query}\n\n"
                "Generate SQL queries that will provide the data needed to "
                "answer each question. Return only the SQL query string(s), "
                "separated by semicolons if multiple queries are needed. "
                "Do not include explanations."
            )
            
            messages = [
                {"role": "system", "content": "You are a SQL expert."},
                {"role": "user", "content": prompt}
            ]
            
            sql_response = llm_client.generate_completion(messages)
            return {"status": "success", "data": sql_response}
        elif operation == "llm_answer":
            # Use LLM to answer questions over the DataFrame
            from app.llm_client import llm_client
            
            # Handle schema and sample parameters if provided
            schema_info = params.get("schema")
            sample_data = params.get("sample")
            
            if schema_info and sample_data:
                # Use schema and sample for better context
                prompt = (
                    "You are a data analysis expert. Given the following "
                    "table schema and sample data, answer the user questions "
                    "as a JSON array of strings.\n\n"
                    f"Table Schema:\n{json.dumps(schema_info, indent=2)}\n\n"
                    f"Sample Data:\n{json.dumps(sample_data, indent=2)}\n\n"
                    f"User Query:\n{params.get('query', '')}\n\n"
                    "Based on the schema and sample, provide specific answers. "
                    "If you need to perform calculations or analysis, describe "
                    "the SQL queries or steps needed. Return only a JSON array "
                    "of strings, no explanations."
                )
            else:
                # Fallback to original DataFrame approach
                data_json = df.head(30).to_json(orient="records")
                user_query = params.get("query", "")
                prompt = (
                    "You are a data analysis expert. Given the following "
                    "table data (as JSON) and user questions, answer the "
                    "questions as a JSON array of strings.\n\n"
                    f"Table Data (first 30 rows):\n{data_json}\n\n"
                    f"User Query:\n{user_query}\n\n"
                    "Return only a JSON array of strings, no explanations."
                )
            
            messages = [
                {
                    "role": "system", 
                    "content": "You are a helpful data analysis assistant."
                },
                {"role": "user", "content": prompt}
            ]
            llm_response = llm_client.generate_json_response(messages)
            return {"status": "success", "data": llm_response}
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
            
            # Clean numeric data if needed
            if column == "Worldwide gross":
                # Clean the currency values: remove prefixes like 'T', '$', ',' and convert to numeric
                filtered_df[column] = filtered_df[column].astype(str)
                # Remove prefixes like 'T', 'A', etc. and clean currency formatting
                filtered_df[column] = filtered_df[column].str.replace(r'^[A-Z]+', '', regex=True)
                filtered_df[column] = filtered_df[column].str.replace(r'[\$,]', '', regex=True)
                # Extract just the first number if there are multiple values separated by space/parentheses
                filtered_df[column] = filtered_df[column].str.extract(r'([\d.]+)')[0]
                filtered_df[column] = pd.to_numeric(filtered_df[column], errors='coerce')
            
            if isinstance(condition, dict):
                # Complex conditions
                if "gt" in condition:
                    filtered_df = filtered_df[filtered_df[column] > condition["gt"]]
                if "gte" in condition:
                    filtered_df = filtered_df[filtered_df[column] >= condition["gte"]]
                if "lt" in condition:
                    filtered_df = filtered_df[filtered_df[column] < condition["lt"]]
                if "lte" in condition:
                    filtered_df = filtered_df[filtered_df[column] <= condition["lte"]]
                if "eq" in condition:
                    filtered_df = filtered_df[filtered_df[column] == condition["eq"]]
                if "in" in condition:
                    filtered_df = filtered_df[filtered_df[column].isin(condition["in"])]
                if "contains" in condition:
                    filtered_df = filtered_df[filtered_df[column].str.contains(condition["contains"], na=False)]
            elif isinstance(condition, str):
                # String-based filtering for complex conditions like ">=2000000000"
                if condition.startswith(">="):
                    value = float(condition[2:])
                    filtered_df = filtered_df[filtered_df[column] >= value]
                elif condition.startswith("<="):
                    value = float(condition[2:])
                    filtered_df = filtered_df[filtered_df[column] <= value]
                elif condition.startswith(">"):
                    value = float(condition[1:])
                    filtered_df = filtered_df[filtered_df[column] > value]
                elif condition.startswith("<"):
                    value = float(condition[1:])
                    filtered_df = filtered_df[filtered_df[column] < value]
                elif condition.startswith("=="):
                    value = float(condition[2:])
                    filtered_df = filtered_df[filtered_df[column] == value]
                else:
                    # String equality or contains
                    if filtered_df[column].dtype == 'object':
                        filtered_df = filtered_df[filtered_df[column].str.contains(str(condition), na=False)]
                    else:
                        filtered_df = filtered_df[filtered_df[column] == condition]
            else:
                # Simple equality
                filtered_df = filtered_df[filtered_df[column] == condition]
        
        return {
            "status": "success",
            "data": filtered_df.to_dict("records"),
            "count": len(filtered_df),
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
