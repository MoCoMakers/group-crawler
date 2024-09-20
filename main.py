import yaml
from bs4 import BeautifulSoup
import time
import requests
import datetime
import pytz as tz
import logging
import json
import calendarManager as calm

logging.basicConfig(filename='debug.log', level=logging.INFO)

with open('groups.yaml', 'r') as myfile:
    group_parameters = yaml.safe_load(myfile)

calendar_groups = group_parameters["calendar_groups"]
print(len(calendar_groups))

def get_html(url):
    response = requests.get(url)
    return response.text




def get_timezone_from_abbreviation(abbreviation):
    # Mapping of common timezone abbreviations to pytz timezones
    timezone_mapping = {
        'EST': 'US/Eastern',
        'EDT': 'US/Eastern',
        'CST': 'US/Central',
        'CDT': 'US/Central',
        'MST': 'US/Mountain',
        'MDT': 'US/Mountain',
        'PST': 'US/Pacific',
        'PDT': 'US/Pacific',
        'UTC': 'UTC'
    }
    result = tz.timezone(timezone_mapping.get(abbreviation, 'UTC'))
    return result

def timestr_to_datetime(date_string):
    # Used for start_time
    # "Sun, Oct 6, 2024, 11:30 PM UTC"
    # or 
    # Used for end_time
    # Thursday, September 19, 2024 at 8:00 PM EDT"


    # Work around for non-padded display days and hours
    date_split = date_string.split(", ")
    month_day = date_split[1] # Oct 6 or September 19
    month_day = month_day.split(" ")
    month = month_day[0]
    day = month_day[1].rjust(2, '0')
    year = date_split[2]
    if " at " in year:
        year_block = year.split(" at ")
        year = year_block[0]
        time_block = year_block[1]
    else:
        time_block = date_split[3]
    
    time_block = time_block.split(":")
    time_block = time_block[0].rjust(2, '0')+":"+time_block[1]

    date_string = month+" "+day+" "+year+" "+time_block
    
    timez_abbrev = date_string[-3:]
    timezone = get_timezone_from_abbreviation(timez_abbrev)
    date_string=date_string[:-4]

    try:
        # "Sept 19 2024 at 8:00 PM"
        date_format = "%b %d %Y %I:%M %p"
        parsed_date = datetime.datetime.strptime(date_string, date_format)
    except ValueError:
        # "September 19 2024 at 8:00 PM"
        date_format = "%B %d %Y %I:%M %p"
        parsed_date = datetime.datetime.strptime(date_string, date_format)
    parsed_date = parsed_date.replace(tzinfo=timezone)
    # Standardize timezone now to Eastern
    parsed_date = parsed_date.astimezone(tz.timezone('US/Eastern'))
    return parsed_date

def parseRSCDateString(full_date):
    # Input: Oct 30, 2024, 5:00 PM – 6:30 PM
    date_group = full_date.split(', ')
    time_group = date_group[2].split(' – ')

    # Target: "Sun, Oct 6, 2024, 11:30 PM UTC"

    start_date_string = "Junk, "+date_group[0]+", "+date_group[1] +", " + time_group[0]+" EST"
    end_date_string = "Junk, "+date_group[0]+", "+date_group[1] +", "+time_group[1]+" EST"

    startTime = timestr_to_datetime(start_date_string)
    endTime = timestr_to_datetime(end_date_string)

    return (startTime, endTime)

def json_str_to_datetime(date_string):
    date_format = "%Y-%m-%dT%H:%M:%S%z"
    parsed_date = datetime.datetime.strptime(date_string, date_format)
    parsed_date = parsed_date.astimezone(tz.timezone('US/Eastern'))
    return parsed_date

class Event():
    def __init__(self, title, description, eventUrl, startTime, endTime, eventStatus="ACTIVE",featuredPhoto=None, meetupId=None,eventType="PHYSICAL", groupName="", gtype="",tags=[]):
        self.title = title
        self.description = description
        self.eventUrl = eventUrl
        self.startTime = startTime
        self.endTime = endTime
        self.eventStatus = eventStatus
        self.featuredPhoto = featuredPhoto
        self.meetupId = meetupId
        self.eventType = eventType
        self.groupName = groupName
        self.gtype = gtype
        self.tags = tags

def fetch_meetup_event(url):
    print(url)
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    json_block = soup.find('script', attrs={'id': '__NEXT_DATA__'})
    json_block = json_block.text
    event_json = json.loads(json_block)
    event = event_json["props"]["pageProps"]["event"]
    id = event["id"]
    
    title = event["title"]
    description = event["description"]
    eventUrl = event["eventUrl"]
    featuredPhoto = event["featuredEventPhoto"]["source"]
    # "2024-09-19T18:00:00-04:00"
    startTime = event["dateTime"]
    # e.g. "2024-09-22T21:30:00-04:00"
    startTime = json_str_to_datetime(startTime)
    endTime = event["endTime"]
    endTime = json_str_to_datetime(endTime)
    # e.g. "PHYSICAL"
    eventType = event["eventType"]
    # e.g. "ACTIVE"
    eventStatus = event["status"]
    myEvent = Event(title,description, eventUrl, startTime,endTime, eventType=eventType, eventStatus=eventStatus, meetupId=id, featuredPhoto=featuredPhoto)
    return myEvent

# DEPRICATED
def fetch_event_end_time(url):
    logging.info(url)
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    info_block = soup.find('div', attrs={'id': 'event-info'})
    info_block = info_block.find_next('time')
    end_time = info_block.text.split(' to ')[1]
    end_time = timestr_to_datetime(end_time)
    return end_time

def fetch_meetup_events(url):
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    # Find the <div> with id 'submain'
    submain_div = soup.find('div', id='submain')

    # Find the <ul> with class 'w-full' that is below the <div> with id 'submain'
    ul_tag = submain_div.find_next('ul', class_='w-full')
    events_list = []
    if ul_tag:
        li_tags = ul_tag.findChildren('li', recursive=False)
        for event_li in li_tags:
            # title = event_li.find('span').text
            # #e.g. Sun, Oct 6, 2024, 11:30 PM UTC
            # event_start_time = event_li.find('time').text
            link = event_li.find('a').get('href').split("?")[0]
            logging.info("Event link: "+link)
            
            current_event = fetch_meetup_event(link)
            events_list.append(current_event)
            time.sleep(1)
    else:
        events_list = [] 
    time.sleep(3)
    return events_list

def fetch_rsc_website_events(url):
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    # Find the <div> with id 'submain'
    events_widget = soup.find('div', id='wix-events-widget')
    ul_tag = events_widget.find_next('ul', attrs={'data-hook': 'events-cards'})
    print("before UL")
    print(ul_tag)
    events_list = []
    if ul_tag:
        li_tags = ul_tag.findChildren('li', recursive=False)
        for event_li in li_tags:
            title_section = event_li.find('div', attrs={'data-hook': 'title'})
            event_title = title_section.find('a').text
            event_link = title_section.find('a')['href']
            print(event_title)
            print(event_link)
            details_section = event_li.find('div', attrs={'data-hook': 'details'})
            # e.g. Oct 30, 2024, 5:00 PM – 6:30 PM
            full_date = details_section.find('div', attrs={'data-hook': 'date'} ).text
            startTime, endTime = parseRSCDateString(full_date)
            description = details_section.find('div', attrs={'data-hook': 'description'} ).text
            if not description:
                description = ""

            current_event = Event(title=event_title, description=description, eventUrl=event_link, startTime=startTime,endTime=endTime)
            events_list.append(current_event)
    else:
        events_list = [] 
    time.sleep(3)
    return events_list
    

def fetch_all_events():
    all_events = []
    for group_section in calendar_groups:
        print("Ingesting group index: "+str(group_section))
        group = calendar_groups[group_section]
        gtype = group["type"]
        name = group["name"]
        tags = group["tags"]
        suggested_priority = group["priority"]
        url = group["all_events_url"]
        if gtype=="meetup":
            events = fetch_meetup_events(url)
            for event in events:
                event.groupName = name
                event.gtype = gtype
                event.tags = tags
            all_events = all_events + events
        elif gtype == "rsc-custom":
            events = fetch_rsc_website_events(url)
            for event in events:
                event.groupName = name
                event.gtype = gtype
                event.tags = tags
            all_events = all_events + events
        else:
            raise Exception("Invalide group type found at index: "+str(group_section))
    return all_events

if __name__=="__main__":
    cal = calm.init_calendar()

    all_events = fetch_all_events()
    # Add events to the calendar
    for event in all_events:
        summary = event.title
        description = event.description
        start = event.startTime
        end = event.endTime
        location = event.eventUrl 
        organizer_email = ""
        organizer_name = event.groupName

        event = calm.create_event(summary, description, start, end, location, organizer_email, organizer_name)
        cal.add_component(event)

    # Write to .ics file
    with open('my_calendar.ics', 'wb') as f:
        f.write(cal.to_ical())

    print("iCalendar file created successfully.")