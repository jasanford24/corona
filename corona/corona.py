#  Raspberry Pi 4B

from pickle import dump, load
from time import localtime, sleep
import pandas as pd

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client


def collect_worldometer():
    URL = 'https://www.worldometers.info/coronavirus/country/us/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    results = soup.find(id='usa_table_countries_today')
    test = results.find_all('td')
    column_heads = results.find_all('th')
    
    # Gets number of recovered cases
    # recovered = soup.find_all(class_="maincounter-number")[-1].text.strip()
    
    # Gets number of columns, in case they change the size of the table
    column_num = len(column_heads)
    
    
    # Unhappy with this section.  I know there's a better way to do this.
    table = []
    list = []
    count = 0

    for x in column_heads:
        list.append(x.text.strip())

    table.append(list)
    list = []

    for x in test:
        if count < column_num:
            if x.text.strip() == '':
                list.append('0')
            else:
                list.append(x.text.strip().replace('+','').replace(',',''))
        else:
            table.append(list)
            list = []
            if x.text.strip() == '':
                list.append('0')
            else:
                list.append(x.text.strip().replace('+','').replace(',',''))
            count = 0
        count += 1
    
    table.append(list)
    table = [x[:-1] for x in table]
    table = pd.DataFrame(table[1:], columns=table[0])
    table.set_index(table['USAState'], inplace=True)
    table.pop('USAState')
    
    return table


def collect_county_count():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    #options.binary_location = '/usr/bin/chromium-browser'
    #driver_path = 'chromedriver'
    options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
    driver_path = '/Users/noumenari/Documents/Python Projects/chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get(
        'https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html'
    )

    # Clicks "Show More" button to show all county data
    element = baby_driver.find_element_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/button')
    baby_driver.execute_script("arguments[0].click();", element)

    # Collects county data and transforms it.
    states = baby_driver.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/table')
    county_df = [x for x in states[0].text.split('\n')]
    if 'COUNTY' not in county_df[0]:
        emergency("NYTimes Collection failed.")

    baby_driver.close()
    return county_df


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
    
    
    def set_data(self, table, prior):
        self.total_cases = table.iloc[-1]['TotalCases']
        self.total_deaths = table.iloc[-1]['TotalDeaths']
        self.total_new_deaths = str(int(table['TotalDeaths'][-1]) - prior['TotalDeaths'][-1])
        
        self.state_case_count = table.loc[self.state]['TotalCases']
        self.state_death_count = table.loc[self.state]['TotalDeaths']
        self.state_new_deaths = str(int(table['TotalDeaths'][self.state]) - prior['TotalDeaths'][self.state])
    
    
    def set_county_data(self, county_df):
        temp = county_df[0].split()
        for x in county_df[1:]:
            t = len(self.state) + 1
            if self.county == x[t:t + len(self.county)]:
                try:
                    self.county_case_count = x.split()[temp.index('CASES') - len(temp)].replace(',','')
                    self.county_death_count = x.split()[temp.index('DEATHS') - len(temp)].replace(',','')
                except:
                    emergency("NYT removed county cases/deaths")
    
    
    def build_message(self):
        message  = 'Covid-19'
        message += '\nU.S. - ' + f"{int(self.total_cases):,d}"
        message += '\nDeaths: ' + f"{int(self.total_deaths):,d}"
        if self.total_new_deaths != '0':
            message += ' (+' + f"{int(self.total_new_deaths):,d}" + ')'
        message += '\n' + self.state + ' - '
        message += f"{int(self.state_case_count):,d}"
        message += '\nDeaths: ' + f"{int(self.state_death_count):,d}"
        if self.state_new_deaths != '0':
            message += ' (+' + f"{int(self.state_new_deaths):,d}" + ')'
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

    message = twilioCli.messages.create(
        body=mess,
        from_=logins[2],
        to=logins[3])
    exit()


# Used to set activiation time to 8pm
def calculate_time():
    eight = 20*60*60
    
    day = 24*60*60
    hour = (60*60)*localtime()[3]
    minute = (60*localtime()[4])
    second = localtime()[5]
    
    time_to_sleep = eight - (hour+minute+second)
    if time_to_sleep < 0:
        return day+time_to_sleep
    return time_to_sleep


def main():
    sleep(calculate_time())
    data = collect_worldometer()
    county_data = collect_county_count()
    
    prior = pd.read_csv('prior_data.csv')
    prior.set_index("USAState", inplace=True)
    
    with open('accounts.p', 'rb') as pfile:
        accounts = load(pfile)
    
    
    for x in accounts:
        recipient = Account(*x)
        recipient.set_data(data, prior)
        recipient.set_county_data(county_data)
        recipient.build_message()
        #print(recipient.message)
        #print(len(recipient.message)+38)
        #print()
        recipient.send_sms()
    
    #emergency(recipient.message)
    
    #data.to_csv('prior_data.csv')


if __name__=="__main__":
    main()
