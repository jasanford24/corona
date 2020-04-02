from random import randint
from pickle import dump, load
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = 'https://www.bennysva.com/locations/benny-pennellos/'

# Load the name data
with open('firstname.p', 'rb') as pfile:
    firstname = load(pfile)
firstname_length = len(firstname) - 1

with open('lastname.p', 'rb') as pfile:
    lastname = load(pfile)
lastname_length = len(lastname) - 1


def main():

    # Load email and request message
    with open('email.p', 'rb') as pfile:
        email = load(pfile)
    email_length = len(email) - 1

    with open('inbox.p', 'rb') as pfile:
        inbox = load(pfile)
    inbox_length = len(inbox) - 1

    # Main webdriver loop
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get(URL)
    element = baby_driver.find_element_by_xpath(
        '/html/body/div[2]/main/section[1]/button')
    baby_driver.execute_script("arguments[0].click();", element)

    # Finds forms to input the data to
    first_name_form = baby_driver.find_element_by_name('input_1.3')
    last_name_form = baby_driver.find_element_by_name('input_1.6')
    email_form = baby_driver.find_element_by_id('input_3_2')
    inbox_form = baby_driver.find_element_by_id('input_3_4')

    # Send random first and last name to webform.
    first_name_form.send_keys(firstname[randint(0, firstname_length)])
    last_name_form.send_keys(lastname[randint(0, lastname_length)].title())

    # pop random email and inbox from list so they don't get reused in the future and
    # send them to the webform
    email_form.send_keys(email.pop(randint(0, email_length)))
    inbox_form.send_keys(inbox.pop(randint(0, inbox_length)))

    # Save updated email and inbox list
    with open('email.p', 'wb') as pfile:
        dump(email, pfile)

    with open('inbox.p', 'wb') as pfile:
        dump(inbox, pfile)

    # Submit webform.
    element = baby_driver.find_element_by_id('gform_submit_button_3')
    baby_driver.execute_script("arguments[0].click();", element)

    # wait 10 seconds to make sure it processes, we're in no rush.
    sleep(10)
    baby_driver.close()

    # sleep the program for random time between 4 and 42 hours
    sleep(randint(60 * 60 * 4, 60 * 60 * 42))
    main()


if __name__ == "__main__":
    main()
