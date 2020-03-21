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
        '//*[@id="coronavirus-us-cases"]/div/div/div[4]/div/button')
    drvr.execute_script("arguments[0].click();", element)

    # Collects state data and transforms it into useable data.
    states = drvr.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[4]/div/table')
    test = [x for x in states[0].text.split('\n')][1:]

    element = drvr.find_element_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/button')
    drvr.execute_script("arguments[0].click();", element)
    states = drvr.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/table')
    temp = [x for x in states[0].text.split('\n')][1:]
    drvr.close()
    logging.warning('Webscrape ending.')
    return test, temp


# Main function that collects the data and sends personalized data to each phone number
def main(update_count):

    # Resets update count for each day
    if localtime()[3] < 10 and update_count != 0:
        update_count[1] = 0
        with open('misc.p', 'wb') as file:
            dump(update_count, file)

    # If after 10am, attempt update. If updated, don't attempt to update again until after 8pm
    if (localtime()[3] > 9 and update_count[1] == 0) or (localtime()[3] > 19 and update_count[1] == 1):

        # Loads collected data
        state_df, county_df = state_count()

        # Total number of deaths and cases in the US
        total_deaths = sum([int(x.replace(',', '').split()[-1]) for x in state_df])
        total_cases = sum([int(x.replace(',','').split()[-1]) for x in county_df])

        # If total number is greater than previous total, send updated text.
        if total_death > update_count[0]:

            logins = login()
            twilioCli = Client(logins[0], logins[1])

            # Load {phone_number:state} data from pickle
            with open('numbers.p', 'rb') as pfile:
                numbers = load(pfile)

            logging.warning('Sending text messages.')

            for k in numbers:
                for x in state_df:
                    if numbers[k][0] in x:
                        death_count = x.split()[-1]
                        case_count = x.split()[-2]
                for x in county_df:
                    if numbers[k][1] in x[len(numbers[k][0])+1:]:
                        county_count = x.split()[-1]
                
                message = 'U.S. Covid-19\nTotal Cases: ' + f"{total_cases:,d}" + \
                            '\nTotal Deaths: ' + f"{total_deaths:,d}" + '\n' + \
                            numbers[k][0] + ":\nCases: " + case_count + "\nDeaths: " + \
                            death_count + "\n" + numbers[k][1] + " County:\nCases: " + county_count
                
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


# Loads previous total death count.
def past():
    with open('misc.p', 'rb') as pfile:
        return load(pfile)


# Loads API data
def login():
    with open('login.p', 'rb') as pfile:
        return load(pfile)


if __name__ == '__main__':
    try:
        main(past())
    except:
        with open('misc.p', 'wb') as file:
            dump([0,0], file)
        main(past())
