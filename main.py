import requests
from datetime import datetime, timedelta
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
from google.protobuf.message import Message
from google.transit import gtfs_realtime_pb2


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
options.disable_hardware_pulse = True
matrix = RGBMatrix(options=options)

def fetch_bus_data():
    """Fetch bus arrival data from MTS API"""
    trip_ids = []
    arrival_times = []
    
    response = requests.get(TRIP_UPDATES_URL + MTS_API_KEY)
    with open("MTS.pb", "wb") as f:
        f.write(response.content) 

    response = requests.get(VEHICLE_POSITIONS_URL + MTS_API_KEY)
    with open("MTS_vehicles.pb", "wb") as f:
        f.write(response.content)

    # Parse the protobuf
    feed = gtfs_realtime_pb2.FeedMessage()
    with open("MTS.pb", "rb") as f:
        feed.ParseFromString(f.read())

    # Extract trip updates
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            trip = entity.trip_update.trip
            for update in entity.trip_update.stop_time_update:
                if update.stop_id == "12896":
                    arrival_time = datetime.fromtimestamp(update.arrival.time)
                    arrival_times.append(arrival_time)
                    trip_ids.append(trip.trip_id)

    arrival_times.sort()
    return arrival_times

def display_bus_info(matrix):
    """Display the next bus arrival time on the LED matrix"""
    try:
        arrival_times = fetch_bus_data()
        
        if not arrival_times:
            display_message(matrix, "No buses found")
            return
        
        # Get the next bus
        next_bus_time = arrival_times[0]
        current_time = datetime.now()
        wait_time_seconds = (next_bus_time - current_time).total_seconds()
        wait_time_minutes = int(wait_time_seconds / 60)
        
        if wait_time_minutes < 0:
            display_message(matrix, "Bus passed")
            return
        
        # Create image for display
        image = Image.new('RGB', (matrix.width, matrix.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Try to use a nice font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
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
        
        # Set the image on the matrix
        matrix.SetImage(image)
        
    except Exception as e:
        display_message(matrix, f"Error: {str(e)[:20]}")

def display_message(matrix, message):
    """Display a simple message on the LED matrix"""
    image = Image.new('RGB', (matrix.width, matrix.height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font = ImageFont.load_default()
    draw.text((2, 12), message, font=font, fill=(255, 0, 0))
    matrix.SetImage(image)

# Main loop
try:
    while True:
        display_bus_info(matrix)
        time.sleep(30)  # Update every 30 seconds
except KeyboardInterrupt:
    matrix.Clear()
