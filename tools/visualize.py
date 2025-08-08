"""
Data visualization tools
"""
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import base64
import io
from app.logger import logger


def visualize(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create data visualizations
    
    Args:
        params: {
            "chart_type": str - "bar", "line", "scatter", "histogram", "pie", "heatmap"
            "data": list/dict - input data
            "x": str - x-axis column
            "y": str - y-axis column
            "color": str - color grouping column
            "title": str - chart title
            "engine": str - "matplotlib" or "plotly"
            "output_format": str - "base64", "html", "json"
            "width": int - chart width
            "height": int - chart height
        }
    """
    try:
        data = params.get("data")
        chart_type = params.get("chart_type", "bar")
        engine = params.get("engine", "plotly")
        
        if not data:
            raise ValueError("data parameter is required")
        
        # Convert data to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        logger.info(f"Creating {chart_type} chart with {engine} engine")
        
        if engine == "plotly":
            return _create_plotly_chart(df, params)
        elif engine == "matplotlib":
            return _create_matplotlib_chart(df, params)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    
    except Exception as e:
        logger.error(f"Visualization failed: {str(e)}")
        return {"status": "error", "error": str(e), "data": None}


def _create_plotly_chart(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create chart using Plotly"""
    try:
        chart_type = params.get("chart_type", "bar")
        x = params.get("x")
        y = params.get("y") 
        color = params.get("color")
        title = params.get("title", f"{chart_type.title()} Chart")
        width = params.get("width", 800)
        height = params.get("height", 600)
        output_format = params.get("output_format", "html")
        
        # Create the chart based on type
        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, color=color, title=title,
                        width=width, height=height)
        
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, color=color, title=title,
                         width=width, height=height)
        
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=title,
                           width=width, height=height)
        
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x, color=color, title=title,
                             width=width, height=height)
        
        elif chart_type == "pie":
            fig = px.pie(df, values=y, names=x, title=title,
                        width=width, height=height)
        
        elif chart_type == "heatmap":
            # Create correlation heatmap for numeric columns
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty:
                raise ValueError("No numeric columns for heatmap")
            
            corr_matrix = numeric_df.corr()
            fig = px.imshow(corr_matrix, text_auto=True, aspect="auto",
                          title=title or "Correlation Heatmap",
                          width=width, height=height)
        
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # Return based on output format
        if output_format == "html":
            html = fig.to_html(include_plotlyjs=True)
            return {
                "status": "success",
                "data": html,
                "metadata": {
                    "chart_type": chart_type,
                    "engine": "plotly",
                    "format": "html"
                }
            }
        
        elif output_format == "json":
            fig_dict = fig.to_dict()
            return {
                "status": "success",
                "data": fig_dict,
                "metadata": {
                    "chart_type": chart_type,
                    "engine": "plotly",
                    "format": "json"
                }
            }
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _create_matplotlib_chart(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create chart using Matplotlib"""
    try:
        chart_type = params.get("chart_type", "bar")
        x = params.get("x")
        y = params.get("y")
        title = params.get("title", f"{chart_type.title()} Chart")
        width = params.get("width", 10)
        height = params.get("height", 6)
        
        # Create figure
        plt.figure(figsize=(width, height))
        
        if chart_type == "bar":
            if x and y:
                plt.bar(df[x], df[y])
                plt.xlabel(x)
                plt.ylabel(y)
            else:
                raise ValueError("x and y parameters required for bar chart")
        
        elif chart_type == "line":
            if x and y:
                plt.plot(df[x], df[y])
                plt.xlabel(x)
                plt.ylabel(y)
            else:
                raise ValueError("x and y parameters required for line chart")
        
        elif chart_type == "scatter":
            if x and y:
                plt.scatter(df[x], df[y])
                plt.xlabel(x)
                plt.ylabel(y)
            else:
                raise ValueError("x and y parameters required for scatter plot")
        
        elif chart_type == "histogram":
            if x:
                plt.hist(df[x], bins=30)
                plt.xlabel(x)
                plt.ylabel("Frequency")
            else:
                raise ValueError("x parameter required for histogram")
        
        elif chart_type == "pie":
            if x and y:
                plt.pie(df[y], labels=df[x], autopct='%1.1f%%')
            else:
                raise ValueError("x and y parameters required for pie chart")
        
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        plt.title(title)
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return {
            "status": "success",
            "data": f"data:image/png;base64,{image_base64}",
            "metadata": {
                "chart_type": chart_type,
                "engine": "matplotlib",
                "format": "base64_png"
            }
        }
    
    except Exception as e:
        plt.close()  # Clean up
        return {"status": "error", "error": str(e)}
