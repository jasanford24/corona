# corona
Corona Virus SMS System for my Raspberry Pi 4B

Checks the New York Times website for Covid-19 data every 30 minutes and\
sends out a text whenever the total number of deaths within the US increases.


Requires Twilio account and additional pickle files:

<pre><code>death.p       -   Int of prior death count
numbers.p     -   Dictionary of numbers with local state {'+phone number' : 'State'}
login.p       -   List of Twilio login credentials with personal number attached on the end
                  for error handling. ['account_sid', 'auth_token', '+phone number']</code></pre>
   
