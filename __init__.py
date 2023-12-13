# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

from . import gui
from .app import App
from .gui.locales import Translator

_ = Translator('init', 'en').lang.gettext

INFO = dict(title=_('CTD-processering'),
            users_directory='users',
            sub_pages=[
                dict(name='PageSimple',
                     title=_('CTD-processering (Förenklad)')),
                dict(name='PageStart',
                     title=_('CTD-processering (Avancerad)')),
                dict(name='PageInspect',
                     title=_('Inspektera och behandla')),
                dict(name='PageEditRaw',
                     title=_('Editera råfiler'))
                       ],
            user_page_class='PageUser')  # Must match name in ALL_PAGES in main app

USER_SETTINGS = []