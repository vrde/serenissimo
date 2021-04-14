import unittest

import check


class TestCheck(unittest.TestCase):
    def test_parse_user_options__choose(self):
        html = """
            <h2 class="centera">Selezionare un servizio</h2>
            <button class="btn btn-primary btn-full" onclick="act_step(2,165)" type="button">Vaccinazione Fragili</button>
            <button class="btn btn-primary btn-full" onclick="act_step(2,179)" type="button">Vaccinazione Vulnerabili</button> 
            <script>toggolaelem();</script>"""

        state, options = check.parse_user_options(html)
        self.assertEqual(state, 'choose')
        self.assertDictEqual(options, {
            'Vaccinazione Fragili': '165',
            'Vaccinazione Vulnerabili': '179'
        })

    def test_parse_user_options__not_eligible(self):
        html = """<div class="alert alert-danger">Attenzione 
non appartieni alle categorie che attualmente possono prenotare

</div>
<div class="centera"><button class="btn btn-primary" onclick="act_step(1);" type="button"><i class="fas fa-undo"></i> Torna indietro</button></div>

<script>toggolaelem();</script>"""

        state, options = check.parse_user_options(html)
        self.assertEqual(state, 'not_eligible')
        self.assertIsNone(options)

    def test_parse_user_options__eligible(self):
        html = """<script>act_step(2,105)</script> """
        state, options = check.parse_user_options(html)
        self.assertEqual(state, 'eligible')
        self.assertEqual(options, '105')


if __name__ == '__main__':
    unittest.main()
