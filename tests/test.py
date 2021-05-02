import unittest

from serenissimo import agent


class TestStep1(unittest.TestCase):
    def test_step_1_parse__eligible(self):
        html = """<script>act_step(2,178)</script> """
        state, url = agent.step_1_parse(html, "XXXXXXXXXXXXXXXX", "0")
        self.assertEqual(state, "eligible")
        self.assertEqual(
            url,
            "https://vaccinicovid.regione.veneto.it/ulss0/azione/sceglisede/servizio/178",
        )

    def test_step_1_parse__not_registered(self):
        html = """
    

    <div class="alert alert-danger">
        
                Il codice fiscale inserito non risulta tra quelli registrati presso questa ULSS. Torna alla <a href="/">homepage</a> e seleziona la tua ULSS di riferimento.
            
    </div>
    <div class="centera"><button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna indietro</button></div>

    <script>toggolaelem();</script>

        """
        with self.assertRaises(agent.NotRegisteredError) as context:
            agent.step_1_parse(html, "XXXXXXXXXXXXXXXX", "0")
        self.assertTrue(
            "Il codice fiscale inserito non risulta tra quelli registrati presso questa ULSS"
            in str(context.exception)
        )

    def test_step_1_parse__already_vaccinated(self):
        html = """
	<div class="alert alert-danger">
		
				Per il codice fiscale inserito &egrave; gi&agrave; iniziato il percorso vaccinale
				
			
	</div>
	<div class="centera"><button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna indietro</button></div>

	<script>toggolaelem();</script>"""
        with self.assertRaises(agent.AlreadyVaccinatedError) as context:
            agent.step_1_parse(html, "XXXXXXXXXXXXXXXX", "0")
        self.assertTrue(
            "Per il codice fiscale inserito è già iniziato il percorso vaccinale"
            in str(context.exception)
        )

    def test_step_1_parse__already_booked(self):
        html = """
	<div class="alert alert-danger">
		
				Per il codice fiscale inserito &egrave; gi&agrave; registrata una prenotazione.
			
	</div>
	<div class="centera"><button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna indietro</button></div>

	<script>toggolaelem();</script>"""

        with self.assertRaises(agent.AlreadyBookedError) as context:
            agent.step_1_parse(html, "XXXXXXXXXXXXXXXX", "0")
        self.assertTrue(
            "Per il codice fiscale inserito è già registrata una prenotazione"
            in str(context.exception)
        )

    def test_step_1_parse__maybe_eligible(self):
        html = """

    <div class="alert alert-danger">
        
                Attenzione non appartieni alle categorie che attualmente possono prenotare
                
                , se ritieni di rientrarci utilizza il pulsante sottostante per accedere al processo di autocertificazione.
                <br><br>
                <div style="text-align:center;">
                <a class="btn btn-danger" href="javascript:sceglicorte()";>Autocertificati</a> 
                </div>
    </div>
    <div class="centera"><button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna indietro</button></div>

    <script>toggolaelem();</script>
    """

    def test_step_1_maybe_eligible(self):
        html = """
	<script>$('#t_des_1').html('<b>XXXXXXXXXXXXXXXX</b>');</script>
	
		<h2 class="centera">Selezionare la categoria per la quale si vuole autocertificarsi</h2>
		<h5>Si ricorda che al momento della vaccinazione verr&agrave; richiesto un documento di identit&agrave; e un autocertificazione che attesti l'effettiva appartenenza alla categoria selezionata</h5>
		<button class="btn btn-primary btn-full"  onclick="inviacf(1105)" type="button">Estremamente vulnerabili nati prima del 1951</button> <button class="btn btn-primary btn-full"  onclick="inviacf(1106)" type="button">Disabili gravi (L.104 art.3 c.3)</button> 
				<div style="text-align:center;padding:10px;">
				<button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna a identificazione</button>
				</div>
				
	<script>toggolaelem();</script>"""

        options = agent.step_1_maybe_eligible(html, "XXXXXXXXXXXXXXXX", 0)
        self.assertDictEqual(
            options,
            {
                "Estremamente vulnerabili nati prima del 1951": "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/1105",
                "Disabili gravi (L.104 art.3 c.3)": "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/1106",
            },
        )

    def test_step_1_eligible(self):
        html = """

    
    <script>$('#t_des_1').html('<b>XXXXXXXXXXXXXXXX</b>');</script>
    
    
    
        <h2 class="centera">Selezionare una sede</h2>
        <button class="btn btn-primary btn-full"  disabled type="button">Chioggia ASPO  [DISPONIBILITA ESAURITA] <br>Via Maestri del Lavoro 50, Chioggia (VE)</button> <button class="btn btn-primary btn-full"  onclick="act_step(3,5)" type="button">Dolo PALAZZETTO DELLO SPORT <br>Viale dello Sport 1, Dolo (VE)</button> <button class="btn btn-primary btn-full"  disabled type="button">Mirano BOCCIODROMO  [DISPONIBILITA ESAURITA] <br>Via G. Matteotti 46, Mirano (VE)</button> <button class="btn btn-primary btn-full"  disabled type="button">Venezia PALA EXPO  [DISPONIBILITA ESAURITA] <br>Via Galileo Ferraris 5, Marghera  (VE)</button> <button class="btn btn-primary btn-full"  disabled type="button">Venezia RAMPA SANTA CHIARA  [DISPONIBILITA ESAURITA] <br>Rampa Santa Chiara, Venezia (ex Sede ACI)</button> 
                <div style="text-align:center;padding:10px;">
                <button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna a identificazione</button>
                </div>
                
        
        
        <script>toggolaelem();</script>


    

    """
        available, unavailable = agent.step_1_eligible(html, "XXXXXXXXXXXXXXXX", 0)
        self.assertEqual(
            available, ["Dolo PALAZZETTO DELLO SPORT Viale dello Sport 1, Dolo (VE)"]
        )
        self.assertEqual(
            unavailable,
            [
                "Chioggia ASPO  [DISPONIBILITA ESAURITA] Via Maestri del Lavoro 50, Chioggia (VE)",
                "Mirano BOCCIODROMO  [DISPONIBILITA ESAURITA] Via G. Matteotti 46, Mirano (VE)",
                "Venezia PALA EXPO  [DISPONIBILITA ESAURITA] Via Galileo Ferraris 5, Marghera  (VE)",
                "Venezia RAMPA SANTA CHIARA  [DISPONIBILITA ESAURITA] Rampa Santa Chiara, Venezia (ex Sede ACI)",
            ],
        )

    def test_step_1_maybe_eligible_cohort(self):
        html = """
	<script>$('#t_des_1').html('<b>XXXXXXXXXXXXXXXX</b>');</script>
	
		<h2 class="centera">Selezionare la categoria per la quale si vuole autocertificarsi</h2>
		<h5>Si ricorda che al momento della vaccinazione verr&agrave; richiesto un documento di identit&agrave; e un autocertificazione che attesti l'effettiva appartenenza alla categoria selezionata</h5>
		<button class="btn btn-primary btn-full"  onclick="inviacf(1105)" type="button">Estremamente vulnerabili nati prima del 1951</button> <button class="btn btn-primary btn-full"  onclick="inviacf(1106)" type="button">Disabili gravi (L.104 art.3 c.3)</button> 
				<div style="text-align:center;padding:10px;">
				<button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna a identificazione</button>
				</div>
				
	<script>toggolaelem();</script>
"""
        pass


if __name__ == "__main__":
    unittest.main()
