#  Pi 4B Version

import logging
from pickle import dump, load
from time import localtime, sleep

import requests
from bs4 import BeautifulSoup
from twilio.rest import Client

logging.basicConfig(filename='debug.log',
                    filemode='w',
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


def collect_worldometer():
    URL = 'https://www.worldometers.info/coronavirus/country/us/'

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    results = soup.find(id='usa_table_countries_today')
    test = results.find_all('td')

    total_cases = test[-7:][-1].text.strip()
    total_deaths = test[-7:][3].text.strip()
    total_recovered = test[-7:][-2].text.strip()
    total_death_change = test[-7:][4].text.strip()

    table = []
    list = []
    count = 0
    for x in test:
        if count < 7:
            list.append(x.text.strip())
        else:
            table.append(list)
            list = []
            list.append(x.text.strip())
            count = 0
        count += 1
    return table, total_cases, total_deaths, total_recovered, total_death_change


# Main function that collects the data and sends personalized data to each phone number
def main(update_count):

    # Resets update count for each day
    if localtime()[3] < 20 and update_count != 0:
        update_count[1] = 0
        with open('misc.p', 'wb') as file:
            dump(update_count, file)

    # If after 10am, attempt update. If updated, don't attempt to update again until after 8pm
    if (localtime()[3] == 19 and update_count[1] == 0):
        sleep(60*59)
        logins = login()
        twilioCli = Client(logins[0], logins[1])

        # Load {phone_number:state} data from pickle
        with open('numbers.p', 'rb') as pfile:
            numbers = load(pfile)

        logging.warning('Sending text messages.')

        table, total_cases, total_deaths, total_recovered, total_death_change = collect_worldometer()
        
        sleep(60)
        
        for k in numbers:
            for x in table:
                if x[0] == numbers[k][0]:
                    state_case_count = x[-1]
                    state_death_count = x[3]
                    state_death_change = x[4]

            for x in county_df:
                if numbers[k][1] in x[len(numbers[k][0]) + 1:]:
                    county_count = x.split()[-1]

            if state_case_count == '':
                state_case_count = '0'
            if state_death_count == '':
                state_death_count = '0'

            message = 'U.S. Covid-19\nActive Cases: ' + total_cases + \
                '\nTotal Deaths: ' + total_deaths

            if total_death_change != '':
                message += ' (+' + total_death_change + ')'

            message += '\nTotal Recovered: ' + total_recovered + '\n' + \
                numbers[k][0] + ":\nCases: " + state_case_count + "\nDeaths: " + \
                state_death_count

            if state_death_change != '':
                message += ' (' + state_death_change + ')'

            message = twilioCli.messages.create(body=message,
                                                from_=logins[2],
                                                to=k)

        update_count[1] += 1
        logging.warning('Messages sent.')

        # Saves updated total death count
        with open('misc.p', 'wb') as file:
            dump(update_count, file)

    sleep_amount = localtime()[4]
    if sleep_amount < 30:
        sleep(1800 - (sleep_amount * 60) - localtime()[5])
    elif sleep_amount >= 30:
        sleep(1800 - ((sleep_amount - 30) * 60) - localtime()[5])
    main(update_count)


# If an error occurs during data collection.
# Sends me a text and shuts program down.
def emergency():
    from sys import exit

    logins = login()
    twilioCli = Client(logins[0], logins[1])

    message = twilioCli.messages.create(body="Something has gone wrong.",
                                        from_=logins[2],
                                        to=logins[3])
    exit()


# Loads previous total death count.
def past():
    try:
        with open('misc.p', 'rb') as pfile:
            return load(pfile)
    except:
        return [0, 0]


# Loads API data
def login():
    with open('login.p', 'rb') as pfile:
        return load(pfile)


if __name__ == '__main__':
    main(past())
