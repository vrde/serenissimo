import unittest

from serenissimo import agent


class TestAgent(unittest.TestCase):
    def test_cohort_selection(self):
        html = """
	<script>$('#t_des_1').html('<b>XXXXXXXXXXXXXXXX</b>');</script>
	
		<h2 class="centera">Selezionare la categoria per la quale si vuole autocertificarsi</h2>
		<h5>Si ricorda che al momento della vaccinazione verr&agrave; richiesto un documento di identit&agrave; e un autocertificazione che attesti l'effettiva appartenenza alla categoria selezionata</h5>
		<button class="btn btn-primary btn-full"  onclick="inviacf(152)" type="button">Vulnerabili</button> <button class="btn btn-primary btn-full"  onclick="inviacf(153)" type="button">Persone con disabilità grave (L. 104 art. 3 c.3)</button> <button class="btn btn-primary btn-full"  onclick="inviacf(154)" type="button">Over 80</button> <button class="btn btn-primary btn-full"  onclick="inviacf(1120)" type="button">Oncologici</button> 
				<div style="text-align:center;padding:10px;">
				<button class="btn btn-primary btn-back" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna a identificazione</button>
				</div>
				
	<script>toggolaelem();</script>

"""
        urls = agent.extract_urls(html, 0)
        self.assertEqual(
            urls,
            [
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/152",
                    "Vulnerabili",
                ],
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/153",
                    "Persone con disabilità grave (L. 104 art. 3 c.3)",
                ],
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/154",
                    "Over 80",
                ],
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/controllocf/corte/1120",
                    "Oncologici",
                ],
            ],
        )

    def test_service(self):
        html = """
	<h2 class="centera">Selezionare un servizio</h2>
	
		<button class="btn btn-primary btn-full" onclick="act_step(2,101)" type="button">Estremamente vulnerabili nati prima del 1951</button> 
		<button class="btn btn-primary btn-full" onclick="act_step(2,614)" type="button">Vulnerabili e Disabili (R)</button> 
			<div style="text-align:center;padding:10px;">
			<button class="btn btn-primary btn-back" onclick="sceglicorte()" type="button"><i class="fas fa-undo"></i> Torna a scelta categoria</button></div>
			
	<script>toggolaelem();</script>"""

        urls = agent.extract_urls(html, 0)
        self.assertEqual(
            urls,
            [
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/sceglisede/servizio/101",
                    "Estremamente vulnerabili nati prima del 1951",
                ],
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/sceglisede/servizio/614",
                    "Vulnerabili e Disabili (R)",
                ],
            ],
        )

    def test_redirect(self):
        html = """<script>act_step(2,608)</script> """
        urls = agent.extract_urls(html, 0)
        self.assertEqual(
            urls,
            [
                [
                    "https://vaccinicovid.regione.veneto.it/ulss0/azione/sceglisede/servizio/608",
                    "",
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
