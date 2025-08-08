"""
Response formatter for different output formats
"""
from typing import Dict, Any, Optional
import json
from app.logger import logger


class ResponseFormatter:
    """Format responses for different output types"""
    
    def format_response(
        self,
        result: Any,
        format_type: str = "json",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format response for output"""
        try:
            if format_type == "json":
                return self._format_json(result, metadata)
            elif format_type == "markdown":
                return self._format_markdown(result, metadata)
            elif format_type == "html":
                return self._format_html(result, metadata)
            elif format_type == "text":
                return self._format_text(result, metadata)
            else:
                logger.warning(f"Unknown format type: {format_type}, using JSON")
                return self._format_json(result, metadata)
                
        except Exception as e:
            logger.error(f"Response formatting failed: {str(e)}")
            return {
                "status": "error",
                "error": f"Formatting failed: {str(e)}",
                "raw_result": str(result)
            }
    
    def _format_json(self, result: Any, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format as JSON"""
        response = {
            "status": "success",
            "data": result,
            "format": "json"
        }
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    def _format_markdown(self, result: Any, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format as Markdown"""
        try:
            markdown_content = self._convert_to_markdown(result)
            
            if metadata:
                markdown_content += f"\n\n## Metadata\n```json\n{json.dumps(metadata, indent=2)}\n```"
            
            return {
                "status": "success",
                "data": markdown_content,
                "format": "markdown"
            }
            
        except Exception as e:
            return self._format_json(result, metadata)
    
    def _format_html(self, result: Any, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format as HTML"""
        try:
            html_content = self._convert_to_html(result)
            
            if metadata:
                html_content += f"<h2>Metadata</h2><pre>{json.dumps(metadata, indent=2)}</pre>"
            
            return {
                "status": "success",
                "data": html_content,
                "format": "html"
            }
            
        except Exception as e:
            return self._format_json(result, metadata)
    
    def _format_text(self, result: Any, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format as plain text"""
        try:
            text_content = self._convert_to_text(result)
            
            if metadata:
                text_content += f"\n\nMetadata:\n{json.dumps(metadata, indent=2)}"
            
            return {
                "status": "success",
                "data": text_content,
                "format": "text"
            }
            
        except Exception as e:
            return self._format_json(result, metadata)
    
    def _convert_to_markdown(self, result: Any) -> str:
        """Convert result to Markdown format"""
        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list):
                # Table-like data
                data = result["data"]
                if data and isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    markdown = "| " + " | ".join(headers) + " |\n"
                    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    
                    for row in data[:10]:  # Limit to first 10 rows
                        markdown += "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n"
                    
                    if len(data) > 10:
                        markdown += f"\n*... and {len(data) - 10} more rows*\n"
                    
                    return markdown
                else:
                    return f"```json\n{json.dumps(result, indent=2)}\n```"
            else:
                return f"```json\n{json.dumps(result, indent=2)}\n```"
        else:
            return str(result)
    
    def _convert_to_html(self, result: Any) -> str:
        """Convert result to HTML format"""
        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list):
                # Table-like data
                data = result["data"]
                if data and isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    html = "<table border='1'><tr>"
                    html += "".join(f"<th>{h}</th>" for h in headers)
                    html += "</tr>"
                    
                    for row in data[:10]:  # Limit to first 10 rows
                        html += "<tr>"
                        html += "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
                        html += "</tr>"
                    
                    html += "</table>"
                    
                    if len(data) > 10:
                        html += f"<p><em>... and {len(data) - 10} more rows</em></p>"
                    
                    return html
                else:
                    return f"<pre>{json.dumps(result, indent=2)}</pre>"
            else:
                return f"<pre>{json.dumps(result, indent=2)}</pre>"
        else:
            return f"<p>{str(result)}</p>"
    
    def _convert_to_text(self, result: Any) -> str:
        """Convert result to plain text format"""
        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list):
                # Table-like data
                data = result["data"]
                if data and isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    text = "\t".join(headers) + "\n"
                    
                    for row in data[:10]:  # Limit to first 10 rows
                        text += "\t".join(str(row.get(h, "")) for h in headers) + "\n"
                    
                    if len(data) > 10:
                        text += f"\n... and {len(data) - 10} more rows\n"
                    
                    return text
                else:
                    return json.dumps(result, indent=2)
            else:
                return json.dumps(result, indent=2)
        else:
            return str(result)


# Global formatter instance
response_formatter = ResponseFormatter()
