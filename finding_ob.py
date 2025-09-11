def ga5_ninth_solution(query=None):
    """
    Extract transcript text from a YouTube video between specified time points.
    
    Args:
        query (str, optional): Query containing custom URL and time range parameters
        
    Returns:
        str: Transcript text from the specified time range
    """
    import re
    from youtube_transcript_api import YouTubeTranscriptApi
    import urllib.parse
    
    print("Starting YouTube transcript extraction...")
    
    # Default parameters
    default_youtube_url = "https://youtu.be/NRntuOJu4ok?si=pdWzx_K5EltiPh0Z"
    default_start_time = 397.2
    default_end_time = 456.1
    youtube_url = default_youtube_url
    start_time = default_start_time
    end_time = default_end_time
    
    # Extract parameters from query if provided
    if query:
        # Extract custom URL if present
        url_match = re.search(r'(https?://(?:www\.)?youtu(?:be\.com|\.be)(?:/watch\?v=|/)[\w\-_]+(?:\?[\w&=]+)?)', query)
        if url_match:
            youtube_url = url_match.group(1)
            print(f"Using custom YouTube URL: {youtube_url}")
        else:
            # Use file_manager to look for URL in query
            url_info = file_manager.detect_file_from_query(query)
            if url_info and url_info.get("path") and "youtu" in url_info.get("path", ""):
                youtube_url = url_info.get("path")
                print(f"Using YouTube URL from file_manager: {youtube_url}")
                
        # Extract time range if present
        time_pattern = r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)'
        time_match = re.search(time_pattern, query)
        if time_match:
            start_time = float(time_match.group(1))
            end_time = float(time_match.group(2))
            print(f"Using custom time range: {start_time} to {end_time} seconds")
        else:
            # Try alternative time formats
            alt_time_pattern = r'(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)'
            alt_time_match = re.search(alt_time_pattern, query)
            if alt_time_match:
                start_time = float(alt_time_match.group(1))
                end_time = float(alt_time_match.group(2))
                print(f"Using custom time range: {start_time} to {end_time} seconds")
    
    # Extract video ID from the URL
    video_id = None
    
    # Check for youtu.be format
    if 'youtu.be' in youtube_url:
        video_id_match = re.search(r'youtu\.be/([^?&]+)', youtube_url)
        if video_id_match:
            video_id = video_id_match.group(1)
    # Check for youtube.com format
    elif 'youtube.com' in youtube_url:
        parsed_url = urllib.parse.urlparse(youtube_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'v' in query_params:
            video_id = query_params['v'][0]
    
    if not video_id:
        video_id = "NRntuOJu4ok"  # Default if extraction fails
        print(f"Could not extract video ID, using default: {video_id}")
    else:
        print(f"Extracted video ID: {video_id}")
    
    try:
        # Get the transcript
        print(f"Fetching transcript for video ID: {video_id}")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Filter transcript entries by time range with margin to avoid truncation
        # Add small margins to ensure we don't cut off words at segment boundaries
        margin = 0.1  # 100ms margin on each side
        filtered_transcript = []
        
        # Use a more inclusive approach to get complete phrases
        for entry in transcript:
            entry_start = entry['start']
            entry_end = entry_start + entry['duration']
            
            # Include entries that start just before end_time and end just after start_time
            if (entry_start <= end_time + margin) and (entry_end >= start_time - margin):
                # For entries that cross the boundaries, only include them if a significant 
                # portion overlaps with our target range
                overlap_duration = min(end_time, entry_end) - max(start_time, entry_start)
                if overlap_duration / entry['duration'] >= 0.3:  # At least 30% overlap
                    filtered_transcript.append(entry)
        
        if not filtered_transcript:
            return f"No transcript text found between {start_time} and {end_time} seconds."
        
        # Sort by start time
        filtered_transcript.sort(key=lambda x: x['start'])
        
        # Process text to ensure we have complete sentences
        raw_texts = [entry['text'] for entry in filtered_transcript]
        
        # Join with proper spacing, ensuring we don't combine words incorrectly
        processed_text = ""
        for i, text in enumerate(raw_texts):
            # Add a space before if this segment doesn't start with punctuation and previous didn't end with it
            if i > 0 and not text.startswith(('.', ',', '!', '?', ':', ';')) and not raw_texts[i-1].endswith(('.', ',', '!', '?', ':', ';', ' ')):
                processed_text += " "
            processed_text += text
        
        # Format for proper readability
        # 1. Fix spacing after periods
        processed_text = re.sub(r'\.(\w)', r'. \1', processed_text)
        
        # 2. Capitalize sentences
        sentence_pattern = r'([.!?])\s+([a-z])'
        processed_text = re.sub(sentence_pattern, lambda m: f"{m.group(1)} {m.group(2).upper()}", processed_text)
        
        # 3. Ensure the first character is capitalized
        if processed_text and processed_text[0].islower():
            processed_text = processed_text[0].upper() + processed_text[1:]
        
        # 4. Clean up any double spaces
        processed_text = re.sub(r'\s{2,}', ' ', processed_text)
        
        print(f"Successfully extracted transcript text between {start_time} and {end_time} seconds")
        return processed_text
        
    except Exception as e:
        import traceback
        print(f"Error extracting transcript: {str(e)}")
        traceback.print_exc()
        
        # Fallback to a sample response if API fails
        return f"""Error extracting transcript: {str(e)}"""
print(ga5_ninth_solution())