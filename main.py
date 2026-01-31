import requests
from datetime import datetime, timedelta
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
from google.protobuf.message import Message
from google.transit import gtfs_realtime_pb2
import os

# Fix SSL certificate issue
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'


MTS_API_KEY = "21a08957-bbfe-4ae8-b0c9-63fbd22953a5"
ORS_CLIENT_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQxNWJjY2JhMjcwZTQ3ODM5ZTljM2EwOTlmM2NmOTFhIiwiaCI6Im11cm11cjY0In0="
TRIP_UPDATES_URL = "https://realtime.sdmts.com/api/api/gtfs_realtime/trip-updates-for-agency/MTS.pb?key="
VEHICLE_POSITIONS_URL = "https://realtime.sdmts.com/api/api/gtfs_realtime/vehicle-positions-for-agency/MTS.pb?key="

BUS_DURATION_MULTIPLIER = 1

# Configure the LED matrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'
options.gpio_slowdown = 2
matrix = RGBMatrix(options=options)
print(f"Matrix initialized: {matrix.width}x{matrix.height}")
print(f"Matrix ready: {matrix}")

def fetch_bus_data():
    """Fetch bus arrival data from MTS API"""
    trip_ids = []
    arrival_times = []
    
    try:
        print("Fetching trip updates...")
        response = requests.get(TRIP_UPDATES_URL + MTS_API_KEY)
        print(f"Trip updates response: {response.status_code}")
        with open("/tmp/MTS.pb", "wb") as f:
            f.write(response.content)
        print(f"Wrote {len(response.content)} bytes to MTS.pb")

        print("Fetching vehicle positions...")
        response = requests.get(VEHICLE_POSITIONS_URL + MTS_API_KEY)
        print(f"Vehicle positions response: {response.status_code}")
        with open("/tmp/MTS_vehicles.pb", "wb") as f:
            f.write(response.content)
        print(f"Wrote {len(response.content)} bytes to MTS_vehicles.pb")

        # Parse the protobuf
        print("Parsing protobuf...")
        feed = gtfs_realtime_pb2.FeedMessage()
        with open("/tmp/MTS.pb", "rb") as f:
            data = f.read()
            print(f"Read {len(data)} bytes from MTS.pb")
            feed.ParseFromString(data)
        print(f"Parsed feed with {len(feed.entity)} entities")

        # Extract trip updates
        print("Extracting trip updates...")
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip = entity.trip_update.trip
                for update in entity.trip_update.stop_time_update:
                    if update.stop_id == "12896":
                        arrival_time = datetime.fromtimestamp(update.arrival.time)
                        arrival_times.append(arrival_time)
                        trip_ids.append(trip.trip_id)

        arrival_times.sort()
        print(f"Total buses for stop 12896: {len(arrival_times)}")
        return arrival_times
    except Exception as e:
        print(f"Error in fetch_bus_data: {e}")
        import traceback
        traceback.print_exc()
        return []

def display_bus_info(matrix):
    """Display the next bus arrival time on the LED matrix"""
    try:
        print("=== Starting display_bus_info ===")
        arrival_times = fetch_bus_data()
        print(f"Found {len(arrival_times)} buses")
        
        if not arrival_times:
            print("No buses found, displaying message")
            display_message(matrix, "No buses found")
            return
        
        # Get the next bus
        next_bus_time = arrival_times[0]
        current_time = datetime.now()
        wait_time_seconds = (next_bus_time - current_time).total_seconds()
        wait_time_minutes = int(wait_time_seconds / 60)
        print(f"Next bus in {wait_time_minutes} minutes at {next_bus_time}")
        
        if wait_time_minutes < 0:
            print("Bus already passed")
            display_message(matrix, "Bus passed")
            return
        
        # Create image for display
        print(f"Creating image ({matrix.width}x{matrix.height})")
        image = Image.new('RGB', (matrix.width, matrix.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            print("Loaded fonts")
        except Exception as font_err:
            print(f"Font error: {font_err}, using default")
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Display "NEXT BUS"
        draw.text((5, 2), "NEXT BUS", font=small_font, fill=(255, 255, 0))
        
        # Display wait time in minutes (large)
        wait_text = str(wait_time_minutes) + "m"
        draw.text((10, 14), wait_text, font=font, fill=(0, 255, 0))
        
        # Display estimated arrival time
        estimated_arrival = next_bus_time + timedelta(seconds=300)
        arrival_text = estimated_arrival.strftime("%I:%M")
        draw.text((5, 28), arrival_text, font=small_font, fill=(255, 100, 255))
        
        print(f"Drawing text: '{wait_text}' at (10,14), '{arrival_text}' at (5,28)")
        # Set the image on the matrix
        matrix.SetImage(image)
        print("Image set on matrix successfully")
        print("=== End display_bus_info ===")
        
    except Exception as e:
        print(f"Error in display_bus_info: {e}")
        import traceback
        traceback.print_exc()
        display_message(matrix, f"Error: {str(e)[:20]}")

def display_message(matrix, message):
    """Display a simple message on the LED matrix"""
    print(f"Displaying message: '{message}'")
    try:
        image = Image.new('RGB', (matrix.width, matrix.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font = ImageFont.load_default()
        draw.text((2, 12), message, font=font, fill=(255, 0, 0))
        matrix.SetImage(image)
        print(f"Message displayed successfully")
    except Exception as e:
        print(f"Error displaying message: {e}")

# Main loop
try:
    # Test display with a simple pattern
    print("Running matrix test...")
    test_image = Image.new('RGB', (matrix.width, matrix.height), color=(0, 0, 0))
    test_draw = ImageDraw.Draw(test_image)
    test_draw.rectangle([0, 0, 10, 10], fill=(255, 0, 0))  # Red square
    test_draw.rectangle([20, 0, 30, 10], fill=(0, 255, 0))  # Green square
    test_draw.rectangle([40, 0, 50, 10], fill=(0, 0, 255))  # Blue square
    matrix.SetImage(test_image)
    print("Test pattern set. Wait 5 seconds to see colored squares...")
    time.sleep(5)
    
    while True:
        print("Fetching bus data...")
        display_bus_info(matrix)
        print("Updated display, sleeping for 30 seconds...")
        time.sleep(30)  # Update every 30 seconds
except KeyboardInterrupt:
    print("Stopping...")
    matrix.Clear()
