#  Raspberry Pi 4B Version

from pickle import dump, load
from time import localtime, sleep

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client


def collect_data():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get('https://coronavirus.1point3acres.com/en')

    # Collect State Data
    states = baby_driver.find_elements_by_xpath(
        '//*[@id="map"]/div[2]/div[1]/div[4]')
    county_df = [x for x in states[0].text.split('\n')][13:]
    county_df = [x.replace(',','') for x in county_df if "+" not in x]
    state_data = pd.DataFrame(
        [county_df[x:x + 4:] for x in range(0, len(county_df), 4)],
        columns=['state', 'cases', 'deaths', 'rate'])

    data = pd.DataFrame(columns=[
        'state', 'county', 'county_cases', 'county_deaths', 'county_rates'
    ])

    for x in range(2,len(state_data)+1):
        # Clicks "Show More" button to show all county data
        element = baby_driver.find_element_by_xpath(
            '//*[@id="map"]/div[2]/div[1]/div[4]/div[' + str(x) +
            ']/div/span[1]')
        baby_driver.execute_script("arguments[0].click();", element)
        # Collects county data and transforms it.
        states = baby_driver.find_elements_by_xpath(
            '//*[@id="map"]/div[2]/div[1]/div[4]/div[' + str(x) +']/div[2]')
        county_df = [x for x in states[0].text.split('\n')]
        county_df = [x.replace(',','') for x in county_df if "+" not in x]
        temp_data = pd.DataFrame(
            [county_df[x:x + 4:] for x in range(0, len(county_df), 4)],
            columns=[
                'county', 'county_cases', 'county_deaths', 'county_rates'
            ])
        temp_data['state'] = state_data['state'][x-2]
        temp_data['state_cases'] = state_data['cases'][x-2]
        temp_data['state_deaths'] = state_data['deaths'][x-2]
        data = data.append(temp_data)

    baby_driver.close()

    data['county_deaths'] = [
        x.replace(',','') if x is not None else '0' for x in data['county_deaths']
    ]
    data['county_cases'] = [
        x.replace(',','') if x is not None else '0' for x in data['county_cases']
    ]
    data.reset_index(inplace=True, drop=True)
    return data


class Account:
    def __init__(self, number, state, county):
        self.number = number
        self.state = state
        self.county = county
        self.message = ''
        self.total_cases = '0'
        self.total_deaths = '0'
        self.total_new_deaths = '0'
        self.state_case_count = '0'
        self.state_death_count = '0'
        self.state_new_deaths = '0'
        self.county_case_count = '0'
        self.county_death_count = '0'

    def set_data(self, data, prior):
        temp_df = data[(data['state'] == self.state)
                       & (data['county'] == self.county)].reset_index(
                           drop=True)
        temp_prior = prior[prior['state'] == self.state].reset_index(drop=True)

        self.total_cases = sum([int(x) for x in data['county_cases']])
        self.total_deaths = sum([int(x) for x in data['county_deaths']])
        self.total_new_deaths = str(
            int(self.total_deaths) - int(prior['state_deaths'][-1:].reset_index(drop=True)[0]))

        self.state_case_count = temp_df['state_cases'][0]
        self.state_death_count = temp_df['state_deaths'][0]
        self.state_new_deaths = str(
            int(self.state_death_count) - int(temp_prior['state_deaths'][0]))

        int(prior[prior['state']==self.state]['state_deaths'].reset_index(drop=True)[0])

        self.county_case_count = temp_df['county_cases'][0]
        self.county_death_count = temp_df['county_deaths'][0]

    def build_message(self):
        message = 'Covid-19'
        message += '\nU.S. - ' + f"{int(self.total_cases):,d}"
        message += '\nDeaths: ' + f"{int(self.total_deaths):,d}"
        if self.total_new_deaths != '0':
            message += ' (+' + f"{int(self.total_new_deaths):,d}" + ')'
        message += '\n' + self.state + ' - '
        message += f"{int(self.state_case_count):,d}"
        message += '\nDeaths: ' + f"{int(self.state_death_count):,d}"
        if self.state_new_deaths != '0':
            message += ' (+' + f"{int(self.state_new_deaths):,d}" + ')'
        if self.county == 'New York':
            message += "\n" + self.county + " City - "
        else:
            message += "\n" + self.county + " - "
        message += f"{int(self.county_case_count):,d}"
        message += "\nDeaths: " + f"{int(self.county_death_count):,d}"
        self.message = message

    def send_sms(self):
        with open('login.p', 'rb') as pfile:
            logins = load(pfile)

        twilioCli = Client(logins[0], logins[1])

        twilioCli.messages.create(body=self.message,
                                  from_=logins[2],
                                  to=self.number)


# If an error occurs during data collection.
# Sends me a text and shuts program down.
def emergency(mess):
    from sys import exit

    with open('login.p', 'rb') as pfile:
        logins = load(pfile)

    twilioCli = Client(logins[0], logins[1])

    message = twilioCli.messages.create(body=mess,
                                        from_=logins[2],
                                        to=logins[3])
    exit()


# Used to set activiation time to 8pm
def calculate_time():
    eight = 20 * 60 * 60

    day = 24 * 60 * 60
    hour = (60 * 60) * localtime()[3]
    minute = (60 * localtime()[4])
    second = localtime()[5]

    time_to_sleep = eight - (hour + minute + second)
    if time_to_sleep < 0:
        return day + time_to_sleep
    return time_to_sleep


def main():
    sleep(calculate_time())

    prior = pd.read_csv('prior_data.csv')
    prior.set_index("USAState", inplace=True)

    data = collect_data()

    with open('accounts.p', 'rb') as pfile:
        accounts = load(pfile)

    for x in accounts:
        recipient = Account(*x)
        recipient.set_data(data, prior)
        recipient.build_message()
        recipient.send_sms()

    data.to_csv('prior_data.csv', index=False)

if __name__ == "__main__":
    main()
