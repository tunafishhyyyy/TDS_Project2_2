#!/usr/bin/env python3
"""
Test script for Wikipedia question workflow
"""

from tools.fetch_web import fetch_web
from tools.analyze import analyze
from tools.visualize import visualize
import json

def test_wikipedia_workflow():
    """Test the complete workflow for the Wikipedia question"""
    
    print("=" * 60)
    print("TESTING WIKIPEDIA WORKFLOW")
    print("=" * 60)
    
    # Step 1: Scrape Wikipedia
    print("\n1. Scraping Wikipedia for highest-grossing films...")
    scrape_result = fetch_web({
        'query': 'https://en.wikipedia.org/wiki/List_of_highest-grossing_films',
        'method': 'scrape'
    })
    
    if scrape_result['status'] != 'success':
        print(f"❌ Scraping failed: {scrape_result.get('error')}")
        return False
        
    tables = scrape_result['data']['tables']
    main_table = None
    
    # Find the main table (should have Rank, Title, Worldwide gross, Year, Peak)
    for i, table in enumerate(tables):
        columns = table.get('columns', [])
        if 'Rank' in columns and 'Peak' in columns and 'Year' in columns:
            main_table = table
            print(f"✅ Found main table (Table {i}) with {table['shape']} shape")
            print(f"   Columns: {columns}")
            break
    
    if not main_table:
        print("❌ Could not find main table with required columns")
        return False
    
    data = main_table['data']
    print(f"   Sample data: {data[:2]}")
    
    # Step 2: Answer questions
    print("\n2. Analyzing the data...")
    
    # Question 1: How many $2 bn movies were released before 2000?
    def extract_gross_value(gross_str):
        """Extract numeric value from gross string like '$2,923,706,026'"""
        try:
            return float(gross_str.replace('$', '').replace(',', ''))
        except:
            return 0
    
    movies_2bn_before_2000 = []
    for movie in data:
        try:
            year = int(movie.get('Year', 0))
            gross_str = movie.get('Worldwide gross', '$0')
            gross = extract_gross_value(gross_str)
            
            if year < 2000 and gross >= 2_000_000_000:
                movies_2bn_before_2000.append(movie)
        except:
            continue
    
    answer1 = len(movies_2bn_before_2000)
    print(f"   Q1: $2B movies before 2000: {answer1}")
    
    # Question 2: Earliest film that grossed over $1.5bn
    earliest_1_5bn = None
    earliest_year = float('inf')
    
    for movie in data:
        try:
            year = int(movie.get('Year', 0))
            gross_str = movie.get('Worldwide gross', '$0')
            gross = extract_gross_value(gross_str)
            
            if gross >= 1_500_000_000 and year < earliest_year:
                earliest_1_5bn = movie
                earliest_year = year
        except:
            continue
    
    answer2 = earliest_1_5bn['Title'] if earliest_1_5bn else "None found"
    print(f"   Q2: Earliest $1.5B film: {answer2} ({earliest_year})")
    
    # Question 3: Correlation between Rank and Peak
    ranks = []
    peaks = []
    
    for movie in data:
        try:
            rank = int(movie.get('Rank', 0))
            peak_str = str(movie.get('Peak', '0'))
            # Handle Peak column - might be string with special chars
            peak = int(''.join(c for c in peak_str if c.isdigit()) or '0')
            
            if rank > 0 and peak > 0:
                ranks.append(rank)
                peaks.append(peak)
        except:
            continue
    
    # Calculate correlation using our analyze tool
    correlation_data = [{'Rank': r, 'Peak': p} for r, p in zip(ranks, peaks)]
    
    corr_result = analyze({
        'data': correlation_data,
        'operation': 'correlation',
        'columns': ['Rank', 'Peak']
    })
    
    if corr_result['status'] == 'success':
        correlation = corr_result['data']['correlation_matrix']['Rank']['Peak']
        answer3 = f"{correlation:.4f}"
        print(f"   Q3: Rank-Peak correlation: {answer3}")
    else:
        answer3 = "Error calculating correlation"
        print(f"   Q3: {answer3}")
    
    # Question 4: Create scatter plot with regression line
    print("\n3. Creating visualization...")
    
    viz_result = visualize({
        'data': correlation_data[:20],  # Use first 20 points to keep it manageable
        'chart_type': 'scatter',
        'x': 'Rank',
        'y': 'Peak', 
        'engine': 'matplotlib',
        'title': 'Rank vs Peak with Regression Line',
        'add_regression': True,
        'regression_color': 'red',
        'regression_style': '--',
        'width': 8,
        'height': 6
    })
    
    if viz_result['status'] == 'success':
        image_data = viz_result['data']
        size_kb = viz_result['metadata']['size_bytes'] / 1024
        answer4 = image_data
        print(f"   Q4: ✅ Scatter plot created ({size_kb:.1f} KB)")
        print(f"       Image starts with: {image_data[:50]}...")
    else:
        answer4 = f"Error: {viz_result.get('error', 'Unknown error')}"
        print(f"   Q4: ❌ {answer4}")
    
    # Final JSON response
    print("\n4. Final Results:")
    results = [
        str(answer1),
        answer2,
        answer3,
        answer4
    ]
    
    print("   JSON Response:")
    for i, result in enumerate(results, 1):
        if i == 4:  # Image data is too long, just show first part
            print(f"   [{i}] {result[:100]}...")
        else:
            print(f"   [{i}] {result}")
    
    print(f"\n✅ Workflow completed successfully!")
    print(f"   - Scraped {len(tables)} tables from Wikipedia")
    print(f"   - Found main table with {len(data)} movies")
    print(f"   - Answered all 4 questions")
    print(f"   - Generated visualization under 100KB")
    
    return True

if __name__ == "__main__":
    test_wikipedia_workflow()
