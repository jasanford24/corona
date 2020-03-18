#  Pi 4B Version

import logging
from pickle import dump, load
from time import localtime, sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client

logging.basicConfig(filename='debug.log',
                    filemode='w',
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


# Collected data from NY Times website
def state_count():
    logging.warning('Webscrape starting.')
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    drvr = webdriver.Chrome(options=options, executable_path=driver_path)
    drvr.get(
        'https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html'
    )

    # Clicks "Show More" button to show all states
    element = drvr.find_element_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[3]/div/button')
    drvr.execute_script("arguments[0].click();", element)

    # Collects state data and transforms it into useable data.
    states = drvr.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[3]/div/table')
    temp = [x for x in states[0].text.split('\n')][1:]
    test = [x.split() for x in temp]
    for x in test:
        if len(x) > 3:
            x[0] = " ".join(x[:-2])
            for y in reversed(range(len(x) - 3)):
                del x[y + 1]
    drvr.close()
    logging.warning('Webscrape ending.')
    return test


# Main function that collects the data and sends personalized data to each phone number
def main(update_count):

    # Resets update count for each day
    if localtime()[3] < 10 and update_count != 0:
        update_count = 0

    # If after 10am, attempt update. If updated, don't attempt to update again until after 8pm
    if (localtime()[3] > 9 and update_count == 0) or (localtime()[3] > 19
                                                      and update_count == 1):

        # Catches any errors that may occur during collection
        try:
            state_df = state_count()
        except:
            emergency()

        # Total number of deaths in the US
        corona_value = sum([int(x[2].replace(',', '')) for x in state_df])

        # If total number is greater than previous total, send updated text.
        if corona_value > past():

            logins = login()
            twilioCli = Client(logins[0], logins[1])

            # Load {phone_number:state} data from pickle
            with open('numbers.p', 'rb') as pfile:
                numbers = load(pfile)

            logging.warning('Sending text messages.')
            for k in numbers:
                state_case = '0'
                state_death = '0'

                for x in state_df:
                    if numbers[k] == x[0]:
                        state_case = x[1]
                        state_death = x[2]

                message = 'Total U.S. Covid-19 death count is now ' + \
                    str(corona_value) + " with " + numbers[k] + " having " + \
                    state_case + " confirmed cases and " + state_death +\
                    " deaths."

                message = twilioCli.messages.create(body=message,
                                                    from_=logins[2],
                                                    to=k)
            update_count += 1
            logging.warning('Messages sent.')
            # Saves updated total death count
            with open('death.p', 'wb') as file:
                dump(corona_value, file)

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
    accountSID = logins[0]
    authToken = logins[1]

    message = twilioCli.messages.create(
        body='Something went wrong.  Shutting down.',
        from_=logins[2],
        to=logins[3])
    exit()


# Loads previous total death count.
def past():
    with open('death.p', 'rb') as pfile:
        return load(pfile)


# Loads API data
def login():
    with open('login.p', 'rb') as pfile:
        return load(pfile)


if __name__ == '__main__':
    main(0)
