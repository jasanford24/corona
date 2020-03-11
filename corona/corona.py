#  Pi 4B Version

from pickle import dump, load
from time import localtime, sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client


# Collected data from NY Times website
def state_count():
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
    return test


# Main function that collects the data and sends personalized data to each phone number
def main():

    # Catches any errors that may occur during collection
    try:
        state_df = state_count()
    except:
        emergency()

    # Total number of deaths in the US
    corona_value = sum([int(x[2]) for x in state_df])

    # If total number is greater than previous total, send updated text.
    if corona_value > past():
        logins = login()

        # Load {phone_number:state} data from pickle
        with open('numbers.p', 'rb') as pfile:
            numbers = load(pfile)

        twilioCli = Client(logins[0], logins[1])

        for k in numbers:
            state_case = '0'
            state_death = '0'

            for x in state_df:
                if numbers[k] == x[0]:
                    state_case = x[1]
                    state_death = x[2]

            # Provides alternate message if home state has the most confirmed cases.
            if numbers[k] == state_df[0][0]:
                message = 'The total number of deaths in the United States from the corona virus is now ' + \
                    str(corona_value) + " with " + numbers[k] + " having the most confirmed cases at " + state_case + " and " + state_death +\
                    " deaths."
            else:
                message = 'The total number of deaths in the United States from the corona virus is now ' + \
                    str(corona_value) + " with " + numbers[k] + " having " + state_case + " confirmed cases and " + state_death +\
                    " deaths."

            message = twilioCli.messages.create(body=message,
                                                from_=logins[2],
                                                to=k)
        save(corona_value)


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


# Saves updated total death count
def save(integers):
    with open('death.p', 'wb') as pfile:
        dump(integers, pfile)


# Loads API data
def login():
    with open('login.p', 'rb') as pfile:
        return load(pfile)


if __name__ == '__main__':
    while True:
        main()
        sleep(1800 - localtime()[5])
