def ga5_seventh_solution(query=None):
    """Count occurrences of a specific key in a nested JSON structure."""
    import json
    import re
    
    print("Starting JSON key occurrence analysis...")
    
    # Default parameters
    default_json_path = "E:\\data science tool\\GA5\\q-extract-nested-json-keys.json"
    target_key = None  # Don't set a default initially
    
    # Look for the actual question at the end of the query
    actual_question = query
    if query:
        # Extract just the last part after the instructions
        query_parts = query.split("Download the data from")
        if len(query_parts) > 1:
            actual_question = query_parts[1]
        print(f"Analyzing question part: {actual_question}")
    
    # Extract key name from the actual question
    if actual_question:
        # Define key extraction patterns
        key_patterns = [
            r'how many times does\s+["\']?([A-Za-z0-9_]+)["\']?\s+appear',
            r'does\s+["\']?([A-Za-z0-9_]+)["\']?\s+appear',
            r'([A-Za-z0-9_]+) appear as a key',
            r'key\s+["\']?([A-Za-z0-9_]+)["\']?',
            r'times\s+does\s+["\']?([A-Za-z0-9_]+)["\']?\s+appear',
            r'occurrences of\s+["\']?([A-Za-z0-9_]+)["\']?'
        ]
        
        # Try each pattern to extract the key
        for pattern in key_patterns:
            key_match = re.search(pattern, actual_question, re.IGNORECASE)
            if key_match:
                extracted_key = key_match.group(1).strip()
                if extracted_key and len(extracted_key) > 1:  # Require at least 2 chars
                    target_key = extracted_key
                    print(f"Key extracted from question: {target_key}")
                    break
    
    # Default to "XF" if no key was found
    if not target_key:
        target_key = "XF"
        print(f"No specific key found in question, using default: {target_key}")
    
    print(f"Final target key for counting: {target_key}")
    
    # Use FileManager to locate and load the JSON file
    json_file_path = file_manager.resolve_file_path(default_json_path, query, "data")
    print(f"Using JSON file: {json_file_path}")
    
    # Function to recursively count key occurrences in nested JSON
    def count_key_occurrences(json_data, key):
        count = 0
        
        if isinstance(json_data, dict):
            # Check keys in this dictionary
            for k in json_data:
                if k == key:
                    count += 1
                # Recursively check the value
                count += count_key_occurrences(json_data[k], key)
                
        elif isinstance(json_data, list):
            # Process each item in the list
            for item in json_data:
                count += count_key_occurrences(item, key)
                
        return count
    
    try:
        # Load the JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        print(f"JSON file loaded successfully")
        
        # Count occurrences of the target key
        key_count = count_key_occurrences(json_data, target_key)
        
        print(f"Found {key_count} occurrences of key '{target_key}'")
        
        # Format and return the result
        return f"{key_count}"
        
    except FileNotFoundError:
        return f"Error: JSON file not found at {json_file_path}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in the file. {str(e)}"
    except Exception as e:
        import traceback
        print(f"Error processing JSON file: {str(e)}")
        traceback.print_exc()
        return f"Error: {str(e)}"
print(ga5_seventh_solution())