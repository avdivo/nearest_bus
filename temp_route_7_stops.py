import json

with open('/home/avdivo/python/nearest_bus/import_schedule/buses/7_aec768be589e56b2b5c7534482026787.json', 'r') as f:
    data = json.load(f)

route_parts = data["7"]

for route_name, stops in route_parts.items():
    stop_list = []
    
    # Sort stops by the number in the key
    sorted_stops = sorted(stops.items(), key=lambda x: int(x[0].split('|')[1]))
    
    for stop_key, stop_data in sorted_stops:
        stop_name = stop_key.split('|')[0]
        stop_id = stop_data['id']
        stop_list.append({"bus_stop": stop_id, "bus_stop_name": stop_name})
        
    print(f"Route: {route_name}")
    print(stop_list)
    print("\n")