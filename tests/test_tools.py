"""
Test suite for tools
"""
import pytest
import pandas as pd
from unittest.mock import patch, mock_open
from tools.fetch_web import fetch_web
from tools.load_local import load_local
from tools.duckdb_runner import duckdb_runner
from tools.analyze import analyze
from tools.visualize import visualize


class TestFetchWeb:
    
    def test_fetch_web_search(self):
        """Test web search functionality"""
        params = {
            "query": "test query",
            "method": "search"
        }
        
        result = fetch_web(params)
        
        assert result["status"] == "success"
        assert "data" in result
        assert "results" in result["data"]
    
    @patch('requests.get')
    def test_fetch_web_scrape(self, mock_get):
        """Test web scraping functionality"""
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test Page</title><body>Content</body></html>"
        mock_response.raise_for_status.return_value = None
        
        params = {
            "query": "https://example.com",
            "method": "scrape",
            "selectors": {"title": "title"}
        }
        
        result = fetch_web(params)
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["title"] == "Test Page"


class TestLoadLocal:
    
    def test_load_csv_success(self):
        """Test CSV loading"""
        csv_content = "name,age\nJohn,25\nJane,30"
        
        with patch('os.path.exists', return_value=True):
            with patch('pandas.read_csv') as mock_read:
                mock_df = pd.DataFrame({"name": ["John", "Jane"], "age": [25, 30]})
                mock_read.return_value = mock_df
                
                params = {"file_path": "/test/data.csv"}
                result = load_local(params)
                
                assert result["status"] == "success"
                assert result["metadata"]["rows"] == 2
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file"""
        params = {"file_path": "/nonexistent/file.csv"}
        
        result = load_local(params)
        
        assert "error" in result
        assert result["data"] is None


class TestDuckDBRunner:
    
    def test_simple_query(self):
        """Test simple SQL query"""
        params = {
            "operation": "query",
            "query": "SELECT 1 as test_col"
        }
        
        result = duckdb_runner(params)
        
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["test_col"] == 1
    
    def test_load_data(self):
        """Test loading data into DuckDB"""
        test_data = [
            {"name": "John", "age": 25},
            {"name": "Jane", "age": 30}
        ]
        
        params = {
            "operation": "load_data",
            "data": test_data,
            "table_name": "test_table"
        }
        
        result = duckdb_runner(params)
        
        assert result["status"] == "success"
        assert result["rows"] == 2


class TestAnalyze:
    
    def test_summary_analysis(self):
        """Test data summary analysis"""
        test_data = [
            {"age": 25, "salary": 50000},
            {"age": 30, "salary": 60000},
            {"age": 35, "salary": 70000}
        ]
        
        params = {
            "operation": "summary",
            "data": test_data,
            "columns": ["age", "salary"]
        }
        
        result = analyze(params)
        
        assert result["status"] == "success"
        assert "basic_stats" in result["data"]
        assert "additional_stats" in result["data"]
    
    def test_filter_data(self):
        """Test data filtering"""
        test_data = [
            {"name": "John", "age": 25},
            {"name": "Jane", "age": 30},
            {"name": "Bob", "age": 35}
        ]
        
        params = {
            "operation": "filter",
            "data": test_data,
            "filters": {"age": {"gt": 27}}
        }
        
        result = analyze(params)
        
        assert result["status"] == "success"
        assert len(result["data"]) == 2
        assert result["metadata"]["filtered_rows"] == 2


class TestVisualize:
    
    def test_bar_chart_plotly(self):
        """Test creating bar chart with Plotly"""
        test_data = [
            {"category": "A", "value": 10},
            {"category": "B", "value": 20},
            {"category": "C", "value": 15}
        ]
        
        params = {
            "chart_type": "bar",
            "data": test_data,
            "x": "category",
            "y": "value",
            "engine": "plotly",
            "output_format": "json"
        }
        
        result = visualize(params)
        
        assert result["status"] == "success"
        assert result["metadata"]["engine"] == "plotly"
        assert result["metadata"]["format"] == "json"
