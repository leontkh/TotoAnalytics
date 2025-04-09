import sys
from scraper import find_query_str

# Call the function to get the query strings
draw_info_list = find_query_str()

# Check if it's a list
print(f"Type of result: {type(draw_info_list)}")
print(f"Number of items: {len(draw_info_list)}")

# Check how many items have draw numbers decoded
draw_nums_found = sum(1 for item in draw_info_list if item.get('draw_number') is not None)
print(f"Entries with decoded draw numbers: {draw_nums_found} out of {len(draw_info_list)}")

# Check the first few items to verify they're dictionaries with the expected keys
if draw_info_list:
    print("\nSample entries:")
    for i, draw_info in enumerate(draw_info_list[:10]):  # Display the first 10 entries
        print(f"\nEntry {i+1}:")
        print(f"  Type: {type(draw_info)}")
        
        # Check if it's a dictionary with the expected keys
        if isinstance(draw_info, dict):
            print(f"  Keys: {', '.join(draw_info.keys())}")
            
            # Display the values
            for key, value in draw_info.items():
                print(f"  {key}: {value}")
                
                # If this is the query_string and it contains a base64 encoded DrawNumber
                if key == 'query_string' and value and value.startswith('sppl='):
                    try:
                        import base64
                        encoded_part = value.split("=")[1]
                        decoded = base64.b64decode(encoded_part).decode('utf-8')
                        print(f"    Decoded: {decoded}")
                    except:
                        pass
        else:
            print(f"  Not a dictionary: {draw_info}")
else:
    print("Error: No results returned")