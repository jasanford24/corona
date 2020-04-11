#  Raspberry Pi 4B Version

from pickle import load
from time import localtime, sleep

import pandas as pd
from multiprocessing import Pool
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client
from sqlalchemy import create_engine


#  Collects data from:
#  https://coronavirus.1point3acres.com/en
#  and stores it in a dataframe.
def collect_data(_):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get('https://coronavirus.1point3acres.com/en')
    xpath_base = '//*[@id="__next"]/div/div[8]'

    # Collect State Data
    states = baby_driver.find_elements_by_xpath(xpath_base)
    county_df = [
        x.strip().replace(',', '') for x in states[0].text.split('\n')
        if "+" not in x and "%" not in x
    ]

    #  Starts collection when it reads "New York" the first state on the list.
    for x in range(len(county_df)):
        if county_df[x] == "New York":
            county_df = county_df[x:]
            break

    header = baby_driver.find_elements_by_xpath(xpath_base + '/header')
    header = header[0].text.split('\n')

    for x in range(0, len(header)):
        if header[x].lower() == "fatality rate" or header[x].lower() == "fatality":
            header.pop(x)
            break
    header_size = len(header)

    #  Stores collected state data in a Pandas dataframe
    state_data = pd.DataFrame(
        [county_df[x:x + header_size:] for x in range(0, len(county_df), header_size)],
        columns=header)

    #  Creates an empty dataframe for county data
    data = pd.DataFrame(
        columns=['state', 'county', 'county_cases', 'county_deaths', 'county_recovered'])

    #  Loops through each state on the website and stores county data
    for x in range(2, len(state_data) + 1):

        # Clicks "Show More" button to show all county data
        element = baby_driver.find_element_by_xpath(
            f'{xpath_base}/div[{x}]/div/span[1]')
        baby_driver.execute_script("arguments[0].click();", element)

        # Collects county data and transforms it.
        states = baby_driver.find_elements_by_xpath(
            f'{xpath_base}/div[{x}]/div[2]')
        county_df = [
            y.strip().replace(',', '') for y in states[0].text.split('\n')
            if "+" not in y and "%" not in y
        ]
        temp_data = pd.DataFrame(
            [county_df[y:y + header_size:] for y in range(0, len(county_df), header_size)],
            columns=['county', 'county_cases', 'county_deaths', 'county_recovered'])
        temp_data['state'] = state_data['Location'][x - 2]
        temp_data['state_cases'] = state_data['Cases'][x - 2]
        temp_data['state_deaths'] = state_data['Deaths'][x - 2]
        temp_data['state_recovered'] = state_data['Recovered'][x - 2]
        data = data.append(temp_data)

    baby_driver.quit()

    return data


# Prior collection does not combine the bay area into one like it does with New York City
# So added this so San Francisco can have a Bay Area count.
def bay_area_collection(_):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get('https://projects.sfchronicle.com/2020/coronavirus-map/')

    states = baby_driver.find_elements_by_xpath(
        '//*[@id="gatsby-focus-wrapper"]/main/div[2]/section/div[1]')

    # Slightly faster than list comprehension
    bay_temp = list(
        map(lambda x: x.replace(',', ''), states[0].text.split('\n')[1::2]))

    baby_driver.quit()
    return bay_temp


# Adds Bay Area data to data dataframe
def add_bay_area(data, bay_area):
    temp = data[data['county'] == 'San Francisco'].reset_index(drop=True)
    temp['county'] = 'Bay Area'
    temp['county_cases'] = bay_area[0]
    temp['county_deaths'] = bay_area[1]
    return temp


#  Practicing Object Programming.
#  Makes an object for each client and prepares their data for delivery
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
        self.county_new_deaths = '0'

    #  Sets individual client data
    def set_data(self, data, prior):
        current_data = data[(data['state'] == self.state)
                            & (data['county'] == self.county)].reset_index(
                                drop=True)

        prior_data = prior[(prior['state'] == self.state)
                           & (prior['county'] == self.county)].reset_index(
                               drop=True)

        self.total_cases = sum([int(x) for x in data['county_cases'][:-1]])
        self.total_deaths = sum([int(x) for x in data['county_deaths'][:-1]])
        self.total_new_deaths = str(
            int(self.total_deaths) -
            sum([int(x) for x in prior['county_deaths'][:-1]]))

        self.state_case_count = current_data['state_cases'][0]
        self.state_death_count = current_data['state_deaths'][0]
        self.state_new_deaths = str(
            int(self.state_death_count) - int(prior_data['state_deaths'][0]))

        self.county_case_count = current_data['county_cases'][0]
        self.county_death_count = current_data['county_deaths'][0]
        self.county_new_deaths = str(
            int(self.county_death_count) - int(prior_data['county_deaths'][0]))
        self.message = self.build_message()

    #  Builds personalized client message
    def build_message(self):
        message = 'US Covid-19'
        message += f"\nCases: {int(self.total_cases):,d}"
        message += f"\nDeaths: {int(self.total_deaths):,d}"

        if self.total_new_deaths != '0':
            message += f" (+{int(self.total_new_deaths):,d})"

        message += f"\n{self.state}"
        message += f"\nCases: {int(self.state_case_count):,d}"
        message += f"\nDeaths: {int(self.state_death_count):,d}"

        if self.state_new_deaths != '0':
            message += f" (+{int(self.state_new_deaths):,d})"

        # If New York, add City for clarity
        if self.county == 'New York':
            message += "\nNew York City"
        else:
            message += f"\n{self.county}"

        message += f"\nCases: {int(self.county_case_count):,d}"
        message += f"\nDeaths: {int(self.county_death_count):,d}"

        if self.county_new_deaths != '0':
            message += f" (+{int(self.county_new_deaths):,d})"
        return message


    #  Sends client message
    def send_sms(self):
        with open('login.p', 'rb') as pfile:
            logins = load(pfile)

        twilioCli = Client(logins[0], logins[1])

        twilioCli.messages.create(body=self.message,
                                  from_=logins[2],
                                  to=self.number)


# Used to set activiation time to 8pmEST
def calculate_time():
    eight = (20 * 60 * 59) - 60  #7:59pm

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

    p = Pool()
    data = p.map_async(collect_data, [1])
    bay = p.map_async(bay_area_collection, [1])
    p.close()
    p.join()

    data = data.get()[0].reset_index(drop=True)
    bay_area = bay.get()[0]

    data = data.append(add_bay_area(data, bay_area), ignore_index=True)

    engine = create_engine('sqlite:///corona-database.db')
    connection = engine.connect()

    prior = pd.read_sql_table(table_name='cases', con=engine)
    accounts = tuple(connection.execute("SELECT * FROM Accounts"))

    for x in accounts:
        recipient = Account(*x)
        recipient.set_data(data, prior)
        recipient.send_sms()

    data.to_sql(name='cases', if_exists='replace', con=engine, index=False)

    connection.close()
    engine.dispose()

    main()


if __name__ == "__main__":
    main()
