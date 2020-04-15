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
        message += f"\nCases: {int(self.total_cases):,}"
        message += f"\nDeaths: {int(self.total_deaths):,}"

        if self.total_new_deaths != '0':
            message += f" (+{int(self.total_new_deaths):,})"

        message += f"\n{self.state}"
        message += f"\nCases: {int(self.state_case_count):,}"
        message += f"\nDeaths: {int(self.state_death_count):,}"

        if self.state_new_deaths != '0':
            message += f" (+{int(self.state_new_deaths):,})"

        # If New York, add City for clarity
        if self.county == 'New York':
            message += "\nNew York City"
        else:
            message += f"\n{self.county}"

        message += f"\nCases: {int(self.county_case_count):,}"
        message += f"\nDeaths: {int(self.county_death_count):,}"

        if self.county_new_deaths != '0':
            message += f" (+{int(self.county_new_deaths):,})"
        return message


    #  Sends client message
    def send_sms(self):
        twilioCli = Client(environ.get("TWILIO_USER"), environ.get("TWILIO_PASS"))

        twilioCli.messages.create(body=self.message,
                                  from_=environ.get("TWILIO_NUMBER"),
                                  to=self.number)
