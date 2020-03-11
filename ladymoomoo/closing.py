import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pickle import dump, load


def fix_input(inp):
    phone = input("Phone number - 10 digits: ")
    test = input('''1   AT&T\n
    2   Sprint\n
    3   T-Mobile\n
    4   Verizon\n
    5   Boost Mobile\n
    6   Cricket\n
    7   Metro PCS\n
    8   Tracfone\n
    9   U.S. Cellular\n
    10  Virgin Mobile
    0   None of the above\n''')

    if inp == '1':
        return phone + '@txt.att.net'
    elif inp == '2':
        return phone + '@messaging.sprintpcs.com'
    elif inp == '3':
        return phone + '@tmomail.net'
    elif inp == '4':
        return phone + '@vtext.com'
    elif inp == '5':
        return phone + '@myboostmobile.com'
    elif inp == '6':
        return phone + '@sms.mycricket.com'
    elif inp == '7':
        return phone + '@mymetropcs.com'
    elif inp == '8':
        return phone + '@mmst5.tracfone.com'
    elif inp == '9':
        return phone + '@email.uscc.net'
    elif inp == '10':
        return phone + '@vmobl.com'
    else:
        print("Go ask for help.")


def add_to_numbers():
    try:
        with open('numbers.p', 'rb') as pfile:
            numbers = load(pfile)
    except FileNotFoundError:
        numbers = []

    numbers.append(input_set(test))

    with open('numbers.p', 'wb') as p:
        dump(numbers, p)


def remove_from_numbers():
    with open('numbers.p', 'rb') as pfile:
        numbers = load(pfile)

    number_to_be_removed = input("Enter 10-digit phone number to be removed: ")

    numbers = [x for x in numbers if x.split('@')[0] != number_to_be_removed]

    with open('numbers.p', 'wb') as p:
        dump(numbers, p)


def send_message(close_time):
    with open('login.p', 'rb') as pfile:
        login = load(pfile)

    with open('numbers.p', 'rb') as pfile:
        numbers = load(pfile)

    smtp = "smtp.gmail.com"
    port = 587

    # This will start our email server
    server = smtplib.SMTP(smtp, port)
    server.ehlo()

    # Starting the server
    server.starttls()

    # Now we need to login
    server.login(login[0], login[1])

    # Now we use the MIME module to structure our message.
    msg = MIMEMultipart()
    msg['From'] = login[0]
    msg['To'] = ", ".join(numbers)
    msg['Subject'] = "Lady Moo Moo Early Closing\n"
    body = "Unfortunately due to the weather, Lady Moo Moo will be closing early today at " + close_time + ".\n"
    msg.attach(MIMEText(body, 'plain'))

    sms = msg.as_string()

    server.sendmail(login[0], numbers, sms)

    # lastly quit the server
    server.quit()


def main():
    answer = input('''1.  Send out closing text.
    2.  Add to list of phone numbers.
    3.  Remove number from list.\n''')
    if answer == '1':
        send_message(input("What time will you be closing? Example '6pm': "))
    elif answer == '2':
        add_to_numbers()
    elif answer == '3':
        remove_from_numbers()


if __name__ == '__main__':
    main()
