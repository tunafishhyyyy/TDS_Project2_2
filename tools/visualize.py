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
    Create visualizations from data
    
    Args:
        params: {
            "data": list/dict - input data
            "plot_type": str - "bar", "line", "scatter", "histogram", etc.
            "x": str - x-axis column
            "y": str - y-axis column
            "title": str - plot title
            "output_format": str - "json", "html", "data_uri"
            "engine": str - "plotly", "matplotlib"
            "regression": bool - add regression line for scatter plots
            "line_style": str - line style for regression
            "line_color": str - line color for regression
            "max_bytes": int - max size for data URI
        }
    """
    try:
        data = params.get("data")
        plot_type = params.get("plot_type", "bar")
        output_format = params.get("output_format", "json")
        engine = params.get("engine", "plotly")
        
        if not data:
            raise ValueError("data parameter is required")
        
        # Convert data to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, dict):
            # Handle different dict formats
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
        
        logger.info(f"Creating {plot_type} chart with {engine} engine")
        
        if engine == "plotly" and plot_type == "scatter":
            try:
                return _create_plotly_chart(df, params)
            except Exception as e:
                logger.warning(f"Plotly failed: {e}. Falling back to matplotlib")
                return _create_matplotlib_chart(df, params)
        elif engine == "plotly":
            try:
                return _create_plotly_chart(df, params)
            except Exception as e:
                logger.warning(f"Plotly failed: {e}. Falling back to matplotlib")
                return _create_matplotlib_chart(df, params)
        else:
            return _create_matplotlib_chart(df, params)
    
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
            
            # Add regression line if requested
            add_regression = params.get("add_regression", False)
            if add_regression and x and y:
                # Calculate regression line
                x_vals = df[x].dropna()
                y_vals = df[y].dropna()
                
                # Align the data
                common_idx = x_vals.index.intersection(y_vals.index)
                x_clean = x_vals.loc[common_idx].values
                y_clean = y_vals.loc[common_idx].values
                
                if len(x_clean) > 1:
                    # Calculate linear regression
                    coeffs = np.polyfit(x_clean, y_clean, 1)
                    regression_line = np.polyval(coeffs, x_clean)
                    
                    # Add regression line trace
                    reg_color = params.get("regression_color", "red")
                    linestyle = params.get("regression_style", "dash")
                    
                    fig.add_scatter(
                        x=x_clean, y=regression_line,
                        mode='lines',
                        name=f'Regression (slope={coeffs[0]:.3f})',
                        line=dict(color=reg_color, dash=linestyle)
                    )
        
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
        
        elif output_format == "data_uri":
            # Export plotly figure to PNG and encode as data URI
            import io, base64
            try:
                img_bytes = fig.to_image(format="png")
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                data_uri = f"data:image/png;base64,{b64}"
                return {
                    "status": "success",
                    "data": data_uri,
                    "metadata": {
                        "chart_type": chart_type,
                        "engine": "plotly",
                        "format": "data_uri"
                    }
                }
            except Exception:
                # Fallback to matplotlib if kaleido not available
                return _create_matplotlib_chart(df, params)
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
                plt.scatter(df[x], df[y], alpha=0.6)
                
                # Add regression line if requested
                regression = params.get("regression", False)
                if regression:
                    # Calculate regression line
                    x_vals = df[x].dropna()
                    y_vals = df[y].dropna()
                    
                    # Align the data
                    common_idx = x_vals.index.intersection(y_vals.index)
                    x_clean = x_vals.loc[common_idx]
                    y_clean = y_vals.loc[common_idx]
                    
                    if len(x_clean) > 1:
                        # Calculate linear regression
                        coeffs = np.polyfit(x_clean, y_clean, 1)
                        regression_line = np.polyval(coeffs, x_clean)
                        
                        # Plot regression line
                        linestyle = params.get("line_style", "dotted")
                        # Convert dotted to dashed for matplotlib
                        if linestyle == "dotted":
                            linestyle = ":"
                        elif linestyle == "dashed":
                            linestyle = "--"
                        
                        color = params.get("line_color", "red")
                        plt.plot(x_clean, regression_line, 
                               linestyle=linestyle, color=color, 
                               label=f'Regression Line (slope={coeffs[0]:.3f})')
                        plt.legend()
                
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
        
        # Try different quality settings to keep under 100KB
        for dpi in [100, 80, 60, 40]:
            buffer.seek(0)
            buffer.truncate()
            
            plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            
            image_size = buffer.tell()
            if image_size < 100000:  # Under 100KB
                break
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return {
            "status": "success",
            "data": f"data:image/png;base64,{image_base64}",
            "metadata": {
                "chart_type": chart_type,
                "engine": "matplotlib",
                "format": "base64_png",
                "size_bytes": len(image_base64) * 3 // 4,  # Approx size
                "dpi": dpi
            }
        }
    
    except Exception as e:
        plt.close()  # Clean up
        return {"status": "error", "error": str(e)}
