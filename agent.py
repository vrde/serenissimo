import re
from bs4 import BeautifulSoup

class RecoverableException(Exception): pass
class AgentHTTPException(RecoverableException): pass

class NotRegisteredError(Exception): pass
class UnknownPayload(Exception):
    def __init__(self, message, html, cf, ulss):
        super().__init__(message)
        self.html = html
        self.cf = cf
        self.ulss = ulss


def soupify(html):
    return BeautifulSoup(html, 'html.parser')

def check(cf, ulss):
    # Create new session with cookie jar
    session = requests.Session()
    step_1(session, cf, ulss)


def is_back_button(button):
    onclick_attr = button.attrs.get('onclick', '')
    class_attr = button.attrs.get('class', '')
    return (
        'act_step(1)' in onclick_attr or
        'sceglicorte' in onclick_attr or
        'btn-back' in class_attr
    )


def step_1(session, cf, ulss):
    url_home = 'https://vaccinicovid.regione.veneto.it/ulss{}'
    url_check_code = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf'
    data = {'cod_fiscale': cf}

    # Get cookie
    session.post(url_home.format(ulss))

    # Submit the form
    r = session.post(url_check_code.format(ulss), data=data)
    if r.status_code != 200:
        raise AgentHTTPException()
    html = r.text
    state, next_url = step_1_parse(html)

    # Open the next url
    r = session.post(next_url)
    if r.status_code != 200:
        raise AgentHTTPException()
    html = r.text
    next_url = step_1_next(state, html, cf, ulss)


def step_1_parse(html, cf, ulss):
    # Check if the response is a redirect to step 2
    matches = re.findall(r'act_step\s*\(\s*2\s*,\s*(\d+)', html)
    if len(matches) == 1:
        next_url = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglisede/servizio/{}'
        return 'eligible', next_url.format(ulss, matches[0])

    # Check if the user doesn't belong to the ULSS
    if 'codice fiscale inserito non risulta tra quelli registrati presso questa ULSS' in html:
        raise NotRegisteredError('Il codice fiscale inserito non risulta tra quelli registrati presso questa ULSS.')

    # Check if the user MAY be eligible
    if 'javascript:sceglicorte()' in html:
        next_url = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglicorte/'
        return 'maybe_eligible', next_url.format(ulss)

    raise UnknownPayload('Error checking payload for step 1', html, cf, ulss)


def step_1_next_eligible(state, html, cf, ulss):
    soup = soupify(html)
    locations = {'available': [], 'unavailable': []}
    for button in soup.find_all('button'):
        if is_back_button(button):
            continue
        if 'disabled' in button.attrs:
            locations['unavailable'].append(button.text.strip())
        else:
            locations['available'].append(button.text.strip())
    return locations

def step_1_next_maybe_eligible(state, html, cf, ulss):
    soup = soupify(html)
    next_url ='https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf/corte/{}'
    next_urls = {}
    for button in soup.find_all('button'):
        onclick = button.attrs.get('onclick', '')
        matches = re.findall(r'inviacf\s*\(\s*(\d+)\s*\)', onclick)
        if matches:
            next_urls[button.text] = next_url.format(ulss, matches[0])
    return next_urls