"""
Web fetching and scraping tools
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import json
import time
from app.logger import logger


def fetch_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web scraping and API data retrieval
    
    Args:
        params: {
            "query": str - search query or URL
            "method": str - "scrape" or "api" or "search"
            "selectors": dict - CSS selectors for data extraction
            "headers": dict - HTTP headers
            "timeout": int - request timeout
        }
    """
    try:
        query = params.get("query", "")
        method = params.get("method", "search")
        selectors = params.get("selectors", {})
        headers = params.get("headers", {
            "User-Agent": "Mozilla/5.0 (compatible; DataBot/1.0)"
        })
        timeout = params.get("timeout", 30)
        
        logger.info(f"Fetching web data: {method} - {query}")
        
        if method == "scrape":
            return _scrape_url(query, selectors, headers, timeout)
        elif method == "api":
            return _fetch_api(query, headers, timeout)
        elif method == "search":
            return _search_web(query, headers, timeout)
        else:
            raise ValueError(f"Unknown method: {method}")
            
    except Exception as e:
        logger.error(f"Web fetch failed: {str(e)}")
        return {"error": str(e), "data": None}


def _scrape_url(url: str, selectors: Dict[str, str], 
                headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    """Scrape data from a specific URL"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract data using selectors
        extracted_data = {}
        for key, selector in selectors.items():
            elements = soup.select(selector)
            if elements:
                if len(elements) == 1:
                    extracted_data[key] = elements[0].get_text(strip=True)
                else:
                    extracted_data[key] = [el.get_text(strip=True) 
                                         for el in elements]
            else:
                extracted_data[key] = None
        
        # If no selectors provided, return basic page info
        if not selectors:
            extracted_data = {
                "title": soup.find("title").get_text(strip=True) if soup.find("title") else "",
                "text_content": soup.get_text()[:1000] + "...",
                "links": [urljoin(url, a.get("href", "")) 
                         for a in soup.find_all("a", href=True)][:10]
            }
        
        return {
            "url": url,
            "status": "success",
            "data": extracted_data,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {"error": str(e), "url": url, "data": None}


def _fetch_api(endpoint: str, headers: Dict[str, str], 
               timeout: int) -> Dict[str, Any]:
    """Fetch data from API endpoint"""
    try:
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Try to parse as JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = response.text
        
        return {
            "endpoint": endpoint,
            "status": "success",
            "data": data,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {"error": str(e), "endpoint": endpoint, "data": None}


def _search_web(query: str, headers: Dict[str, str], 
                timeout: int) -> Dict[str, Any]:
    """Search for information (mock implementation)"""
    # This is a simplified mock - in production you'd use:
    # - Google Search API
    # - Bing Search API
    # - SerpAPI
    # - Custom search engines
    
    try:
        # Mock search results
        mock_results = [
            {
                "title": f"Result for {query} - Site 1",
                "url": "https://example1.com",
                "snippet": f"Information about {query} can be found here..."
            },
            {
                "title": f"{query} Analysis - Site 2", 
                "url": "https://example2.com",
                "snippet": f"Detailed analysis of {query} with data..."
            }
        ]
        
        logger.warning("Using mock search results - implement real search API")
        
        return {
            "query": query,
            "status": "success", 
            "data": {
                "results": mock_results,
                "count": len(mock_results)
            },
            "timestamp": time.time(),
            "note": "Mock results - implement real search API"
        }
        
    except Exception as e:
        return {"error": str(e), "query": query, "data": None}
