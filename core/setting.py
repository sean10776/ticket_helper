from dataclasses import dataclass
import logging
import json
import pathlib
from typing import Optional, Union

from .utils import TICKET_WEB

__all__ = ['Setting']

logger = logging.getLogger(__name__)
AUTO = None

class Setting:
    APP_VERSION = '0.0.0'
    APP_NAME = 'Ticket Helper'

    def __init__(
        self, 
        setting_path: Optional[Union[str, pathlib.Path]] = AUTO,
        ticket_web: Optional[Union[str, TICKET_WEB]] = TICKET_WEB.DEFAULT,
        auto_login: Optional[bool] = False,
    ):
        if setting_path is AUTO:
            self._setting_path = pathlib.Path('./setting.json')
        else:
            self.setting_path = setting_path
            
        # if setting file exists, load setting from file and return 
        if self.setting_path.exists():
            self.load_setting()
            return

        self.ticket_web = ticket_web
        self.auto_login = auto_login
        self.user_info = User_Info(account='', password='')
        self.save_setting()

    @property
    def setting_path(self):
        return self._setting_path
    
    @setting_path.setter
    def setting_path(self, value):
        self._setting_path = pathlib.Path(value)

    @property
    def ticket_web(self):
        return self._ticket_web
    
    @ticket_web.setter
    def ticket_web(self, value:Union[str, TICKET_WEB]):
        if isinstance(value, TICKET_WEB):
            self._ticket_web = value
        else:
            value = value.upper()
            if value not in TICKET_WEB.__members__: 
                logger.warning(f'Invalid ticket web {value}, set to default')
                self._ticket_web = TICKET_WEB.DEFAULT
                return
            self._ticket_web = TICKET_WEB[value]

    def load_setting(self):
        with open(self.setting_path, 'r') as f:
            setting = json.load(f)
            self.ticket_web = setting.get('ticket_web', TICKET_WEB.DEFAULT)
            self.auto_login = setting.get('auto_login', False)
            user_info = setting.get('user_info', None)
            self.user_info = None
            if user_info:
                self.user_info = User_Info(**user_info)
        
    def save_setting(self):
        with open(self.setting_path, 'w') as f:
            f.write(self.__repr__())

    def __repr__(self):
        '''
        convert setting arguments to json format
        '''
        return json.dumps({
            'ticket_web': self._ticket_web.name.upper(),
            'auto_login': self.auto_login,
            'user_info': self.user_info.__dict__,
        }, indent=4)

@dataclass
class User_Info:
    account: str
    password: str