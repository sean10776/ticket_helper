from dataclasses import dataclass
from enum import Enum

@dataclass
class WEB_INFO:
    home_url: str
    login_url: str

class TICKET_WEB(Enum):
    TIXCRAFT = WEB_INFO(home_url='https://tixcraft.com/', login_url='')
    KKTIX = WEB_INFO(home_url='https://kktix.com', login_url='')
    KHAM = WEB_INFO(home_url='https://www.kham.com.tw/', login_url='https://kham.com.tw/application/utk13/utk1306_.aspx')
    DEFAULT = TIXCRAFT