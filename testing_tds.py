# import json
# from collections import defaultdict

# # Path to your JSON file
# json_file_path = "e:\\data science tool\\main\\grok\\ip_logs.json"

# # Dictionary to store unique IP-endpoint combinations
# ip_endpoint_map = defaultdict(set)

# # Load and process the JSON data
# with open(json_file_path, 'r') as file:
#     logs = json.load(file)
    
#     # Extract unique IP and endpoint combinations
#     for entry in logs:
#         ip = entry.get("ip_address")
#         endpoint = entry.get("endpoint")
#         time = entry.get('timestamp')
#         if ip and endpoint:
#             ip_endpoint_map[ip].add(endpoint)

# # Output the results
# print(f"Found {len(ip_endpoint_map)} unique IP addresses:")
# print("-" * 50)

# for ip, endpoints in ip_endpoint_map.items():
#     print(f"IP: {ip}")
#     print(f"Accessed endpoints: {', '.join(endpoints)}")
#     print("-" * 50)
import json
from collections import defaultdict

# Path to your JSON file
json_file_path = "e:\\data science tool\\main\\grok\\ip_logs.json"

# Dictionary to store unique IP-endpoint combinations
ip_endpoint_map = defaultdict(set)

# Dictionary to store counts of /api/ accesses per IP
api_access_count = defaultdict(int)

# Load and process the JSON data
with open(json_file_path, 'r') as file:
    logs = json.load(file)
    
    # Extract unique IP and endpoint combinations
    for entry in logs:
        ip = entry.get("ip_address")
        endpoint = entry.get("endpoint")
        time = entry.get('timestamp')
        
        if ip and endpoint:
            ip_endpoint_map[ip].add(endpoint)
            
            # Count /api/ accesses specifically
            if endpoint == "/api/":
                api_access_count[ip] += 1

# Output the results
print(f"Found {len(ip_endpoint_map)} unique IP addresses:")
print("-" * 50)

for ip, endpoints in ip_endpoint_map.items():
    print(f"IP: {ip}")
    print(f"Accessed endpoints: {', '.join(endpoints)}")
    
    # Show API access count if there were any
    if api_access_count[ip] > 0:
        print(f"API endpoint access count: {api_access_count[ip]}")
    
    print("-" * 50)

# Summary of API access
total_api_calls = sum(api_access_count.values())
print(f"\nTotal /api/ endpoint calls: {total_api_calls}")
print(f"IPs accessing /api/ endpoint: {len(api_access_count)}")