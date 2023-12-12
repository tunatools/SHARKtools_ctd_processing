import gettext
import pathlib
class Translator:
    def __init__(self, domain, language):
        self.language = language
        self.domain = domain
        self.lang = gettext.translation(self.domain, localedir=pathlib.Path(__file__).parent, languages=[self.language])
        self.lang.install()
