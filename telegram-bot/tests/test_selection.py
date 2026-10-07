import itertools
import unittest

from bot import select_markup
from guide import DATA, SELECT_STEPS, select_plan, select_text


class SelectionTest(unittest.TestCase):
    def test_all_answer_combinations(self):
        questions = DATA['en']['selection']['questions']
        for values in itertools.product(*(questions[key]['options'] for key in SELECT_STEPS)):
            answers = dict(zip(SELECT_STEPS, values))
            with self.subTest(answers=answers):
                if answers['sites'] != 'one' or answers['need'] in ('launch', 'custom', 'unsure') or answers['mode'] == 'unsure':
                    expected = 'custom'
                elif answers['mode'] == 'one_time':
                    expected = 'one_time'
                elif answers['need'] == 'content':
                    expected = 'content'
                else:
                    expected = 'technical'
                self.assertEqual(select_plan(answers)[0], expected)
                for language in DATA:
                    text = select_text(language, answers)
                    self.assertLess(len(text.encode('utf-16-le')) // 2, 4096)
                    buttons = select_markup(language, answers, 3).inline_keyboard
                    self.assertEqual(buttons[0][0].callback_data, 'quote:selection:' + expected)

    def test_content_and_buttons(self):
        for language in DATA:
            questions = DATA[language]['selection']['questions']
            for step, key in enumerate(SELECT_STEPS):
                self.assertEqual(set(questions[key]['options']),
                                 set(DATA['en']['selection']['questions'][key]['options']))
                for row in select_markup(language, {}, step).inline_keyboard:
                    for button in row:
                        self.assertLessEqual(len(button.callback_data.encode()), 64)
        self.assertEqual(select_plan({})[0], 'custom')
