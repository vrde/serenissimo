import requests
import re
import logging
from bs4 import BeautifulSoup

log = logging.getLogger()

URL_ULSS = 'https://vaccinicovid.regione.veneto.it/ulss{}'
URL_CHECK_CF = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf'
URL_SERVICE = 'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglisede/servizio/{}'


def parse_user_options(html):
    # User is not eligible when they are sent back to step 1
    if 'act_step(1)' in html:
        return 'not_eligible', None

    # User needs to choose their category
    if 'Selezionare un servizio' in html:
        options = {}
        soup = BeautifulSoup(html, 'html.parser')
        for button in soup.find_all('button'):
            label = button.text
            onclick = button.attrs.get('onclick')
            if onclick:
                m = re.findall('act_step\(2,(\d+)\)', onclick)
                option_id = m[0]
                options[label] = option_id
        return 'choose', options

    # User can move to step 2, extract the option id
    if '<script>act_step(2,' in html:
        m = re.findall('act_step\(2,(\d+)\)', html)
        option_id = m[0]
        return 'eligible', option_id

    # Should be 'inziato il percorso di vaccinazione' (note the typo). The typo
    # might be fixed at one point, so we check only for the rest of the string
    if 'il percorso di vaccinazione' in html:
        return 'already_vaccinated', None


def check_user_options(session, cf, ulss):
    data = {'cod_fiscale': cf}

    # Get cookie
    session.post(URL_ULSS.format(ulss))

    # Get options
    r = session.post(URL_CHECK_CF.format(ulss), data=data)
    html = r.text

    return parse_user_options(html)


def parse_locations(html):
    soup = BeautifulSoup(html, 'html.parser')
    locations = []
    disabled_locations = []
    for b in soup.find_all('button'):
        if 'disabled' not in b.attrs:
            locations.append(b.text.strip())
        else:
            disabled_locations.append(b.text.strip())
    if locations:
        log.info('Enabled locations %s', ', '.join(locations))
    if disabled_locations:
        log.info('Disabled locations %s', ', '.join(disabled_locations))
    if len(locations) == 1 and locations[0].strip() == 'Torna indietro':
        return []
    return locations


def find_locations(session, cf, ulss, service):
    data = {'cod_fiscale': cf}
    r = session.post(URL_SERVICE.format(ulss, service), data=data)
    locations = parse_locations(r.text)
    return locations


def check(cf, ulss):
    # Create new session with cookie jar
    session = requests.Session()

    state, options = check_user_options(session, cf, ulss)

    # User is not eligible
    if state == 'not_eligible':
        return state, []

    # User is already vaccinated
    if state == 'already_vaccinated':
        return state, []

    # User is in a special category, we show everything and add a label so the
    # user doesn't need to choose.
    if state == 'choose':
        locations = []
        for label, option_id in options.items():
            option_locations = find_locations(session, cf, ulss, option_id)
            locations_with_label = [
                '{} ({})'.format(l, label)
                for l in option_locations]
            locations.extend(locations_with_label)
        return 'eligible_special', locations

    # User is eligible
    if state == 'eligible':
        return 'eligible', find_locations(session, cf, ulss, options)
