from dataclasses import dataclass
from enum import Enum

from .ticket_flow import Ticket_Flow_Kham

@dataclass
class WEB_INFO:
    home_url: str
    login_url: str

class TICKET_WEB(Enum):
    TIXCRAFT = WEB_INFO(home_url='https://tixcraft.com/', login_url='')
    KKTIX = WEB_INFO(home_url='https://kktix.com', login_url='')
    KHAM = WEB_INFO(home_url=Ticket_Flow_Kham.HOME_URL, login_url=Ticket_Flow_Kham.LOGIN_URL)
    DEFAULT = TIXCRAFT