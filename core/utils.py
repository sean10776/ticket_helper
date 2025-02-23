from dataclasses import dataclass
from enum import Enum

class TICKET_WEB(Enum):
    TIXCRAFT = 0
    KKTIX = 1
    KHAM = 2
    DEFAULT = TIXCRAFT

@dataclass
class User_Info:
    account: str
    password: str

    @classmethod
    def default(cls):
        return cls(
            account='enter your account',
            password='enter your password'
        )

@dataclass
class KKTIX_Argument:
    event_page: str
    ticket_name: str
    num_of_ticket: int

    @property
    def valid_page_url(self):
        return self.event_page.startswith('https') and self.event_page.endswith('registrations/new')

    @classmethod
    def default(cls):
        return cls(
            event_page="enter event url like: 'https://kktix.com/events/{event_id}/registrations/new'",
            ticket_name="enter ticket name",
            num_of_ticket=0
        )