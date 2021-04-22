import re
import requests
from bs4 import BeautifulSoup


class RecoverableException(Exception): pass
class AgentHTTPException(RecoverableException): pass

class UnknownPayload(Exception):
    def __init__(self, message, html, cf, ulss):
        super().__init__(message)
        self.html = html
        self.cf = cf
        self.ulss = ulss


URL_COHORT_CHOOSE = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglicorte/'
URL_COHORT_SELECT = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf/corte/{}'
URL_SERVICE = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglisede/servizio/{}'

def check(cf, ulss):
    session = requests.Session()
    url_home = 'https://vaccinicovid.regione.veneto.it/ulss{}'
    url_check_code = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf'
    data = {'cod_fiscale': cf}

    # Get cookie
    session.get(url_home.format(ulss))

    # Submit the form
    r = session.post(url_check_code.format(ulss), data=data)
    if r.status_code != 200:
        raise AgentHTTPException()
    html = r.text
    state, url = start(html, cf, ulss)
    if url is None:
        return state, [], []
    else:
        return state, *locations(session, url, ulss)

def locations(session, url, ulss, max_depth=5):
    print(' '*(5-max_depth), url)
    if max_depth == 0:
        return [], []

    r = session.post(url)
    if r.status_code != 200:
        raise AgentHTTPException()
    html = r.text
    if 'sceglisede' in url:
        available, unavailable = extract_locations(html)
    else:
        available, unavailable = [], []
        for url, label in extract_urls(html, ulss):
            new_available, new_unavailable = locations(session, url, ulss, max_depth=max_depth-1)
            available.extend('{} {}'.format(label, l) for l in new_available)
            unavailable.extend('{} {}'.format(label, l) for l in new_unavailable)
    return available, unavailable


def start(html, cf, ulss):
    # Check if the response is a redirect to step 2
    matches = re.findall(r'act_step\(2,(\d+)', html.replace(" ", ""))
    if len(matches) == 1:
        next_url = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglisede/servizio/{}'
        return 'eligible', next_url.format(ulss, matches[0])

    # Check if the user doesn't belong to the ULSS
    if 'codice fiscale inserito non risulta tra quelli registrati presso questa ULSS' in html:
        return 'not_registered', None

    if 'Per il codice fiscale inserito &egrave; gi&agrave; iniziato il percorso vaccinale' in html:
        return 'already_vaccinated', None

    if 'Per il codice fiscale inserito &egrave; gi&agrave; registrata una prenotazione' in html:
        return 'already_booked', None

    # Check if the user MAY be eligible
    if ('Attenzione non appartieni alle categorie che attualmente possono prenotare' in html and
        'javascript:sceglicorte()' in html):
        next_url = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglicorte/'
        return 'maybe_eligible', next_url.format(ulss)

    raise UnknownPayload('Error checking payload for step 1', html, cf, ulss)


def soupify(html):
    return BeautifulSoup(html, 'html.parser')

def extract_urls(html, ulss):
    soup = soupify(html)
    urls = []

    if html.replace(" ", "").startswith('<script>act_step(2,'):
        matches = re.findall(r'act_step\(2,(\d+)\)', html.replace(" ", ""))
        if matches:
            urls.append([URL_SERVICE.format(ulss, matches[0]), ''])

    for button in soup.find_all('button'):
        onclick = button.attrs.get('onclick', '')
        matches = re.findall(r'act_step\(2,(\d+)\)', onclick.replace(" ", ""))
        if matches:
            urls.append([URL_SERVICE.format(ulss, matches[0]), button.text])

    for button in soup.find_all('button'):
        onclick = button.attrs.get('onclick', '')
        matches = re.findall(r'inviacf\((\d+)\)', onclick.replace(" ", ""))
        if matches:
            urls.append([URL_COHORT_SELECT.format(ulss, matches[0]), button.text])

    return urls

def is_back_button(button):
    onclick_attr = button.attrs.get('onclick', '')
    class_attr = button.attrs.get('class', '')
    return (
        'act_step(1)' in onclick_attr or
        'sceglicorte' in onclick_attr or
        'btn-back' in class_attr
    )


def extract_locations(html):
    soup = soupify(html)
    available = []
    unavailable = []
    for button in soup.find_all('button'):
        if is_back_button(button):
            continue
        if 'disabled' in button.attrs:
            unavailable.append(button.text.strip())
        else:
            available.append(button.text.strip())
    return available, unavailable