#!/usr/bin/env python3

import json
import tempfile
import os
from planner.planner_client import PlannerClient

def test_performance_improvements():
    """Test the performance and cost tracking improvements"""
    
    # Create a test question that mentions TB-scale data
    question_content = """
The Indian high court dataset contains ~16M judgments (~1TB of data).

Analyze this data efficiently and answer:
1. Which high court disposed the most cases from 2019-2022?
2. Calculate regression slope for court 33_10 delay analysis
3. Create a visualization 

IMPORTANT: Avoid loading full dataset due to size constraints.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(question_content.strip())
        question_file = f.name
    
    try:
        # Initialize planner
        planner = PlannerClient()
        
        # Test with question file
        print("Testing improved planner with performance optimization...")
        plan = planner.generate_plan("", context={}, question_file=question_file)
        
        print(f"\n=== EXECUTION PLAN ===")
        print(f"Generated plan with {len(plan.steps)} steps")
        
        # Check for performance optimizations 
        problematic_queries = []
        good_queries = []
        
        for i, step in enumerate(plan.steps, 1):
            if step.tool.value == 'duckdb_runner' and 'query' in step.params:
                query = step.params['query']
                if 'SELECT *' in query:
                    problematic_queries.append(f"Step {i}: Contains SELECT *")
                else:
                    good_queries.append(f"Step {i}: Uses aggregation/filtering")
                
                print(f"  Step {i}: {step.tool.value}")
                # Show first 100 chars of query
                query_preview = query[:100] + "..." if len(query) > 100 else query
                print(f"    Query: {query_preview}")
        
        # Display statistics
        if plan.planning_stats:
            print(f"\n=== PLANNING STATISTICS ===")
            for key, value in plan.planning_stats.items():
                print(f"  {key}: {value}")
        
        # Performance assessment
        print(f"\n=== PERFORMANCE ASSESSMENT ===")
        print(f"✅ Good queries (aggregated): {len(good_queries)}")
        print(f"⚠️ Problematic queries (SELECT *): {len(problematic_queries)}")
        
        if problematic_queries:
            print("\nProblematic queries detected:")
            for issue in problematic_queries:
                print(f"  - {issue}")
        
        return len(problematic_queries) == 0
        
    finally:
        # Cleanup
        if os.path.exists(question_file):
            os.unlink(question_file)

if __name__ == "__main__":
    success = test_performance_improvements()
    if success:
        print(f"\n🎉 Test PASSED - No performance issues detected!")
    else:
        print(f"\n⚠️ Test WARNING - Performance issues found!")
