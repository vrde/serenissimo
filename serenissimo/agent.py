import re
from collections import defaultdict

import requests
from bs4 import BeautifulSoup


class RecoverableException(Exception):
    pass


class AgentHTTPException(RecoverableException):
    pass


class UnknownPayload(Exception):
    def __init__(self, message, html, cf, ulss):
        super().__init__(message)
        self.html = html
        self.cf = cf
        self.ulss = ulss


URL_ROOT = "https://vaccinicovid.regione.veneto.it"
URL_ULSS = URL_ROOT + "/ulss{}"
URL_COHORT_CHOOSE = URL_ULSS + "/azione/sceglicorte/"
URL_COHORT_SELECT = URL_ULSS + "/azione/controllocf/corte/{}"
URL_SERVICE = URL_ULSS + "/azione/sceglisede/servizio/{}"
URL_CHECK = URL_ULSS + "/azione/controllocf"


def check(ulss, fiscal_code, health_insurance_number):
    try:
        return _check(ulss, fiscal_code, health_insurance_number)
    except requests.exceptions.RequestException:
        raise AgentHTTPException()


def _check(ulss, fiscal_code, health_insurance_number):
    session = requests.Session()
    data = {"cod_fiscale": fiscal_code, "num_tessera": health_insurance_number}

    # Get cookie
    session.get(URL_ULSS.format(ulss))

    # Submit the form
    r = session.post(URL_CHECK.format(ulss), data=data)
    if r.status_code != 200:
        raise AgentHTTPException()
    html = r.text

    # Ginepraio time!
    try:
        state, url = start(html, fiscal_code, ulss)
    except UnknownPayload as e:
        # Seems like ULSS 1 has a different "start" page, so we try to extract locations
        # directly from the html
        state = "maybe_eligible"
        available, unavailable = locations(session, None, ulss, html=html)
        if not available and not unavailable:
            raise e
        return state, available, unavailable

    if url is None:
        return state, None, None
    else:
        available, unavailable = locations(session, url, ulss)
        return state, available, unavailable


def locations(session, url, ulss, max_depth=5, html=None):
    if max_depth == 0:
        return None, None

    if html is None:
        r = session.post(url)
        if r.status_code != 200:
            raise AgentHTTPException()
        html = r.text

    if url and "sceglisede" in url:
        available, unavailable = extract_locations(html)
    else:
        available, unavailable = {}, {}
        for url, label in extract_urls(html, ulss):
            sub_available, sub_unavailable = locations(
                session, url, ulss, max_depth=max_depth - 1
            )
            if sub_available:
                available[label] = sub_available
            if sub_unavailable:
                unavailable[label] = sub_unavailable

        # Yes this can be done better
        available_keys = list(available.keys())
        unavailable_keys = list(unavailable.keys())
        if available_keys and available_keys[0] == "":
            available = available[""]
        if unavailable_keys and unavailable_keys[0] == "":
            unavailable = unavailable[""]

    return available, unavailable


def start(html, cf, ulss):
    # Check if the response is a redirect to step 2
    matches = re.findall(r"act_step\(2,(\d+)", html.replace(" ", ""))
    if len(matches) == 1:
        return "eligible", URL_SERVICE.format(ulss, matches[0])

    # Check if the user doesn't belong to the ULSS
    if (
        "codice fiscale inserito non risulta tra quelli registrati presso questa ULSS"
        in html
    ):
        return "not_registered", None

    if "Il numero tessera non risulta valido per il codice fiscale indicato" in html:
        return "wrong_health_insurance_number", None

    if (
        "Per il codice fiscale inserito &egrave; gi&agrave; iniziato il percorso vaccinale"
        in html
    ):
        return "already_vaccinated", None

    if (
        "Per il codice fiscale inserito &egrave; gi&agrave; registrata una prenotazione"
        in html
    ):
        return "already_booked", None

    # Check if the user MAY be eligible
    if (
        "Attenzione non appartieni alle categorie che attualmente possono prenotare"
        in html
        and "javascript:sceglicorte()" in html
    ):
        return "maybe_eligible", URL_COHORT_CHOOSE.format(ulss)

    if (
        "Attenzione non appartieni alle categorie che attualmente possono prenotare"
        in html
        and "act_step(1)" in html
    ):
        return "not_eligible", None

    raise UnknownPayload("Error understanding payload", html, cf, ulss)


def soupify(html):
    return BeautifulSoup(html, "html.parser")


def extract_urls(html, ulss):
    soup = soupify(html)
    urls = []

    if html.replace(" ", "").startswith("<script>act_step(2,"):
        matches = re.findall(r"act_step\(2,(\d+)\)", html.replace(" ", ""))
        if matches:
            urls.append([URL_SERVICE.format(ulss, matches[0]), ""])

    for button in soup.find_all("button"):
        onclick = button.attrs.get("onclick", "")
        matches = re.findall(r"act_step\(2,(\d+)\)", onclick.replace(" ", ""))
        if matches:
            urls.append([URL_SERVICE.format(ulss, matches[0]), button.text])

    for button in soup.find_all("button"):
        onclick = button.attrs.get("onclick", "")
        matches = re.findall(r"inviacf\((\d+)\)", onclick.replace(" ", ""))
        if matches:
            urls.append([URL_COHORT_SELECT.format(ulss, matches[0]), button.text])

    return urls


def is_back_button(button):
    onclick_attr = button.attrs.get("onclick", "")
    class_attr = button.attrs.get("class", "")
    return (
        "act_step(1)" in onclick_attr
        or "sceglicorte" in onclick_attr
        or "btn-back" in class_attr
    )


def extract_locations(html):
    soup = soupify(html)
    available = []
    unavailable = []
    for button in soup.find_all("button"):
        if is_back_button(button):
            continue
        if "disabled" in button.attrs:
            unavailable.append(button.text.strip())
        else:
            available.append(button.text.strip())
    return available, unavailable


def format_locations(locations, indent=0, limit=1024):
    message = _format_locations(locations, indent=indent)
    truncated = str(BeautifulSoup(message[:limit], "html.parser"))
    if len(message) != len(truncated):
        truncated = (
            f"{truncated}…\n<i>Nota: il messaggio è troppo lungo e l'ho troncato</i>"
        )
    return truncated


def _format_locations(locations, indent=0):
    if not locations:
        return ""
    b = []
    spacing = " " * indent
    if isinstance(locations, dict):
        keys = sorted(locations.keys())
        for k in keys:
            v = locations[k]
            b.append(f"{spacing}<i><u>{k}</u></i>:")
            b.append(format_locations(v, indent=indent + 2))
            b.append("")
    else:
        for l in locations:
            b.append("{}- {}".format(spacing, l))
    return "\n".join(b)


STATE_TO_LABEL = {
    "eligible": "Puoi prenotarti per il vaccino",
    "not_eligible": "Non puoi ancora prenotarti per il vaccino",
    "maybe_eligible": "Puoi prenotarti per il vaccino solo se sei in una categoria speciale",
    "not_registered": "Il tuo Codice Fiscale non appartiene alla ULSS che hai specificato",
    "already_vaccinated": "Sei già stato vaccinato",
    "already_booked": "Hai già prenotato il vaccino",
}


def format_state(state):
    return STATE_TO_LABEL[state]