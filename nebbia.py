import requests
import json
from pprint import pprint

# 1. Define Search Parameters
ZURICH_LAT = 47.3769  # Approximate center latitude for Zurich
ZURICH_LON = 8.5417   # Approximate center longitude for Zurich
RADIUS_KM = 45
RADIUS_M = RADIUS_KM * 1000

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Open-Elevation API endpoint (Note: Reliability can vary)
ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# meters
FOG_LIMIT=400

def get_restaurants_from_osm():
    """Queries Overpass API for restaurants around Zürich."""
    print(f"-> Querying OpenStreetMap for restaurants within {RADIUS_KM}km of Zürich...")

    # Overpass Query Language (QL)
    overpass_query = f"""
        [out:json][timeout:60];
        // Define the area (15km around the coordinates)
        node(around:{RADIUS_M},{ZURICH_LAT},{ZURICH_LON})["amenity"="restaurant"]->.nodes;
        way(around:{RADIUS_M},{ZURICH_LAT},{ZURICH_LON})["amenity"="restaurant"]->.ways;
        relation(around:{RADIUS_M},{ZURICH_LAT},{ZURICH_LON})["amenity"="restaurant"]->.relations;

        // Combine all and print the center of each feature
        (.nodes; .ways; .relations;);
        out center;
    """
    # 
    
    response = requests.post(OVERPASS_URL, data={'data': overpass_query})
    
    if response.status_code != 200:
        print(f"Error querying Overpass API: Status Code {response.status_code}")
        return []

    data = response.json()
    restaurants = []

    for element in data['elements']:
        # Extract name and coordinates
        name = element['tags'].get('name', 'N/A')
        # Use 'lat'/'lon' for nodes, or 'center' coordinates for ways/relations
        lat = element.get('lat') or element.get('center', {}).get('lat')
        lon = element.get('lon') or element.get('center', {}).get('lon')
        print(element)
        if lat and lon:
            restaurants.append({
                'name': name,
                'lat': lat,
                'lon': lon,
                'elevation': None  # Placeholder for elevation data
            })
    
    print(f"-> Found {len(restaurants)} restaurant features.")
    return restaurants


def get_elevation_for_points(restaurants):
    """Fetches elevation data for a list of coordinates."""
    
    if not restaurants:
        return []

    print(f"-> Fetching elevation for {len(restaurants)} coordinates...")
    
    # The Open-Elevation API takes a list of locations in its body
    locations = [{'latitude': r['lat'], 'longitude': r['lon']} for r in restaurants]
    
    try:
        response = requests.post(ELEVATION_URL, 
                                 json={'locations': locations}, 
                                 headers={'Content-Type': 'application/json'},
                                 timeout=30)
        
        if response.status_code != 200:
            print(f"Error querying Elevation API: Status Code {response.status_code}")
            # Return original list with None elevation
            return restaurants 

        elevation_data = response.json().get('results', [])
        
        # Merge the elevation results back into the restaurant data
        for i, result in enumerate(elevation_data):
            el = result.get('elevation', 'N/A') 
            restaurants[i]['elevation'] = el
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during API request: {e}")

    return restaurants


def main():
    """Main function to run the process."""
    
    # Step 1: Get restaurant data (names and coordinates)
    restaurants_data = get_restaurants_from_osm()
    
    # Step 2: Get elevation data
    final_data = get_elevation_for_points(restaurants_data)

    # Step 3: Print the results
    print("\n--- Final Results (First 10) ---")
    pprint(list(filter(lambda x : x['elevation']>FOG_LIMIT, final_data) ))
    
    # Optional: Save to a file
    with open('zurich_restaurants_with_elevation.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print("\nData saved to zurich_restaurants_with_elevation.json")

if __name__ == "__main__":
    main()
    