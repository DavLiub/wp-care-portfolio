import unittest
from datetime import date

from bot import faq_markup, menu_markup
from guide import DATA, faq_text, find_question, normalize_question


class FaqTest(unittest.TestCase):
    def test_content_contract(self):
        self.assertEqual(set(DATA['ru']['faq']['questions']), set(DATA['en']['faq']['questions']))
        for language in DATA:
            faq = DATA[language]['faq']
            date.fromisoformat(faq['reviewed'])
            self.assertEqual(len(faq['questions']), 12)
            for key, item in faq['questions'].items():
                self.assertIn(item['group'], faq['groups'])
                self.assertIn(item['url'], ('https://wp-care.taldav.com/services/',
                                            'https://wp-care.taldav.com/pricing/'))
                self.assertLess(len(faq_text(language, key).encode('utf-16-le')) // 2, 4096)
                for phrase in [item['label'], *item['aliases']]:
                    self.assertEqual(find_question(phrase), key)
                buttons = faq_markup(language, question=key).inline_keyboard
                for row in buttons:
                    for button in row:
                        self.assertLessEqual(len(button.callback_data.encode()), 64)
            actions = [button.callback_data for row in menu_markup(language).inline_keyboard for button in row]
            self.assertIn('faq', actions)

    def test_conservative_matching(self):
        self.assertEqual(find_question('  КАКОЙ ТАРИФ ВЫБРАТЬ??? '), 'choose')
        self.assertEqual(find_question('What costs extra?'), 'extras')
        for text in ('', 'Я не хочу выбирать тариф', 'Please delete my website',
                     'Do you guarantee recovery tomorrow?', 'какие сроки ' * 100):
            self.assertIsNone(find_question(text))
        self.assertEqual(normalize_question('Ещё?'), 'еще')
