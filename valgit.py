#!/usr/bin/env python3
"""
GitHub Actions Workflow Validator
Checks YAML syntax, required fields, and common GitHub Actions errors
"""

import yaml
import sys
import os
import re
from pathlib import Path

def check_yaml_syntax(filepath):
    """Check basic YAML syntax"""
    try:
        with open(filepath, 'r') as file:
            content = file.read()
            return yaml.safe_load(content), content
    except yaml.YAMLError as e:
        print(f"❌ YAML Syntax Error: {e}")
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            print(f"   Line {mark.line + 1}, Column {mark.column + 1}")
        return None, None
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return None, None

def validate_structure(data, filename):
    """Validate GitHub Actions workflow structure"""
    errors = []
    warnings = []
    
    if not isinstance(data, dict):
        errors.append("Root must be a dictionary/mapping")
        return errors, warnings
    
    # Check required top-level fields
    if 'name' not in data:
        warnings.append("No 'name' field - workflow will be named after filename")
    
    if 'on' not in data:
        errors.append("Missing 'on' field - workflow won't trigger")
    elif not data['on']:
        errors.append("'on' field cannot be empty")
    
    if 'jobs' not in data:
        errors.append("Missing 'jobs' field - no jobs to run")
    elif not data['jobs']:
        errors.append("'jobs' field cannot be empty")
    
    return errors, warnings

def validate_jobs(jobs, filename):
    """Validate job configurations"""
    errors = []
    warnings = []
    
    for job_name, job_config in jobs.items():
        # Check job name length
        if len(job_name) > 40:
            warnings.append(f"Job '{job_name}' name is long ({len(job_name)} chars)")
        
        if not isinstance(job_config, dict):
            errors.append(f"Job '{job_name}' must be a dictionary")
            continue
        
        # Check runs-on
        if 'runs-on' not in job_config:
            errors.append(f"Job '{job_name}' missing 'runs-on'")
        else:
            valid_runners = ['ubuntu-latest', 'ubuntu-22.04', 'ubuntu-20.04', 
                           'windows-latest', 'windows-2022', 'macos-latest', 
                           'macos-14', 'macos-13', 'self-hosted']
            runner = job_config['runs-on']
            if runner not in valid_runners and not runner.startswith('ubuntu-'):
                warnings.append(f"Job '{job_name}' uses unusual runner: {runner}")
        
        # Check steps
        if 'steps' not in job_config:
            errors.append(f"Job '{job_name}' missing 'steps'")
        elif not job_config['steps']:
            errors.append(f"Job '{job_name}' has empty steps")
        else:
            validate_steps(job_config['steps'], job_name, errors, warnings)
        
        # Check for deprecated syntax
        if 'needs' in job_config and not isinstance(job_config['needs'], (str, list)):
            errors.append(f"Job '{job_name}': 'needs' must be string or list")
        
        if 'if' in job_config and not isinstance(job_config['if'], str):
            warnings.append(f"Job '{job_name}': 'if' condition should be a string")
    
    return errors, warnings

def validate_steps(steps, job_name, errors, warnings):
    """Validate step configurations"""
    for i, step in enumerate(steps):
        step_num = i + 1
        
        if not isinstance(step, dict):
            errors.append(f"Job '{job_name}', step {step_num}: must be a dictionary")
            continue
        
        # Each step needs either 'uses' or 'run'
        if 'uses' not in step and 'run' not in step:
            errors.append(f"Job '{job_name}', step {step_num}: missing both 'uses' and 'run'")
        
        # Validate 'uses' format
        if 'uses' in step:
            uses = step['uses']
            # Check for common action formats
            if not re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(@[a-zA-Z0-9./-]+)?$', uses) and \
               not uses.startswith('./') and \
               not uses.startswith('docker://'):
                warnings.append(f"Job '{job_name}', step {step_num}: 'uses' looks unusual: {uses}")
        
        # Validate 'with' context
        if 'with' in step and not isinstance(step['with'], dict):
            errors.append(f"Job '{job_name}', step {step_num}: 'with' must be a dictionary")
        
        # Check for missing name (optional but good practice)
        if 'name' not in step and ('run' in step or 'uses' in step):
            warnings.append(f"Job '{job_name}', step {step_num}: consider adding a 'name' field")

def validate_common_actions(data):
    """Validate common action patterns"""
    errors = []
    
    # Check for checkout action
    if 'jobs' in data:
        for job_name, job_config in data['jobs'].items():
            if 'steps' in job_config:
                has_checkout = any(
                    step.get('uses', '').startswith('actions/checkout') 
                    for step in job_config['steps']
                )
                has_git_commands = any(
                    'git' in step.get('run', '') 
                    for step in job_config['steps']
                )
                
                if has_git_commands and not has_checkout:
                    errors.append(f"Job '{job_name}': uses git commands but no actions/checkout step")
    
    return errors

def check_indentation(content, filepath):
    """Check for common indentation issues"""
    lines = content.split('\n')
    issues = []
    
    for i, line in enumerate(lines):
        if line and not line.startswith(' '):
            continue
        
        # Check for mixing spaces and tabs
        if '\t' in line:
            issues.append(f"Line {i+1}: Contains tab character (use spaces only)")
        
        # Check indentation level (should be multiple of 2)
        spaces = len(line) - len(line.lstrip())
        if spaces % 2 != 0:
            issues.append(f"Line {i+1}: Indentation is {spaces} spaces (should be multiple of 2)")
    
    return issues

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate-github-action.py <workflow-file.yml>")
        print("\nExample: python validate-github-action.py .github/workflows/ci.yml")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print(f"🔍 Validating: {filepath}\n")
    print("=" * 50)
    
    # Check YAML syntax
    data, content = check_yaml_syntax(filepath)
    if data is None:
        sys.exit(1)
    
    # Check indentation
    indent_issues = check_indentation(content, filepath)
    if indent_issues:
        print("\n⚠️  Indentation Issues:")
        for issue in indent_issues:
            print(f"   • {issue}")
    
    # Validate structure
    struct_errors, struct_warnings = validate_structure(data, filepath)
    
    # Validate jobs
    job_errors = []
    job_warnings = []
    if 'jobs' in data and data['jobs']:
        job_errors, job_warnings = validate_jobs(data['jobs'], filepath)
    
    # Validate common actions
    action_errors = validate_common_actions(data)
    
    # Combine all errors and warnings
    all_errors = struct_errors + job_errors + action_errors
    all_warnings = struct_warnings + job_warnings
    
    # Print results
    if all_errors:
        print("\n❌ ERRORS (must fix):")
        for error in all_errors:
            print(f"   • {error}")
    
    if all_warnings:
        print("\n⚠️  WARNINGS (consider fixing):")
        for warning in all_warnings:
            print(f"   • {warning}")
    
    if not all_errors and not all_warnings:
        print("\n✅ VALID! No errors or warnings found.")
        print("   Your workflow YAML syntax is correct.")
    elif not all_errors:
        print("\n⚠️  YAML is valid but has warnings.")
    
    print("\n" + "=" * 50)
    
    # Exit with error code if there are errors
    sys.exit(1 if all_errors else 0)

if __name__ == "__main__":
    main()
