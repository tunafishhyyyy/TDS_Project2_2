#!/usr/bin/env python3

import json
import tempfile
import os
from planner.planner_client import PlannerClient

def test_new_task_breakdown():
    """Test the new simple task breakdown approach"""
    
    # Create a test question file
    question_content = """
Please analyze the indian high court data and answer these questions in json format:
{
  "question1": "Which high court disposed of the most cases?",
  "question2": "What is the regression slope between case registration and disposal dates?", 
  "question3": "Create a scatterplot visualization showing this relationship"
}
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(question_content.strip())
        question_file = f.name
    
    try:
        # Initialize planner
        planner = PlannerClient()
        
        # Test with question file
        print("Testing with question file approach...")
        plan = planner.generate_plan("", context={}, question_file=question_file)
        
        print(f"Generated plan with {len(plan.steps)} steps:")
        for i, step in enumerate(plan.steps, 1):
            print(f"  Step {i}: {step.tool} - {step.params}")
            
        return len(plan.steps) > 1
        
    finally:
        # Cleanup
        if os.path.exists(question_file):
            os.unlink(question_file)

if __name__ == "__main__":
    success = test_new_task_breakdown()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
