from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime
import pytz

def init_calendar():
    # Initialize the calendar
    cal = Calendar()
    cal.add('prodid', '-//DMV Petri Dish Events//mocomakers.com//')
    cal.add('version', '2.0')
    return cal

# Function to create an event
def create_event(summary, description, start, end, location, organizer_email, organizer_name):
    event = Event()
    event.add('summary', summary)
    event.add('description', description)
    event.add('dtstart', start)
    event.add('dtend', end)
    event.add('location', location)
    
    organizer = vCalAddress(f'MAILTO:{organizer_email}')
    organizer.params['cn'] = vText(organizer_name)
    organizer.params['role'] = vText('CHAIR')
    event['organizer'] = organizer
    
    event['uid'] = f'{start.strftime("%Y%m%dT%H%M%S")}/{organizer_email}'
    event.add('priority', 5)
    
    return event


