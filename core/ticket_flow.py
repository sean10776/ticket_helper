from abc import abstractmethod
import base64
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import io
import re
from datetime import datetime, timezone
import json

import asyncio
import ddddocr
import logging
import requests
from nodriver import Tab, cdp
import PIL.Image
import requests.cookies

from .setting import Setting
from .utils import TICKET_WEB

__all__ = [
    'Ticket_Flow',
    'get_ticket_flow',
]

logger = logging.getLogger(__name__)

class Ticket_Flow:
    HOME_URL: str = None
    LOGIN_URL: str = None

    def __init__(
        self,
        page: Tab,
        setting: Setting,
    ):
        self.page = page
        self.setting = setting

    async def start(self):
        if self.setting.auto_login:
            logger.debug(f'Auto login to {self.LOGIN_URL}')
            await self.auto_login()

    @abstractmethod
    async def auto_login(self):
        pass

    @abstractmethod
    async def get_ticket(self):
        pass

    async def sleep(self, seconds: float = 0.25):
        await self.page.sleep(seconds)

    @property
    def stop(self):
        return self.page.closed 
    
    @property
    def can_buy(self):
        False

class Ticket_Flow_Kham(Ticket_Flow):
    HOME_URL='https://www.kham.com.tw/'
    LOGIN_URL='https://kham.com.tw/application/utk13/utk1306_.aspx'

    login_js = '''
        o = {{
            "ACCOUNT": "{account}",
            "PASSWORD": "㎞" + window.btoa("{password}"),
            "CHK": "{chk}",
        }};
        DoPost("action=DO_LOGIN&post=" + encodeURIComponent(JSON.stringify(o)), "/Application/UTK13/UTK1306_.aspx", function(i, n) {{
            hideProcess()
        }})
    '''

    def __init__(
        self,
        page: Tab,
        setting: Setting,
    ):
        super().__init__(page, setting)
        self.ocr = ddddocr.DdddOcr()
        self.captcha_res_id = None
        self.page.add_handler(cdp.network.ResponseReceived, self.__get_response)

    async def __get_response(self, event: cdp.network.ResponseReceived):
        url = event.response.url
        if 'pic.aspx' in url:
            logger.debug(f'captcha url: {url}')
            self.captcha_res_id = event.request_id

    async def __solve_captcha(self, wait_times:int=10)->str:
        counter = 0
        while self.captcha_res_id is None:
            await self.page.sleep(0.5)
            counter += 1
            if counter > wait_times: break
        
        if self.captcha_res_id is None:
            logger.error('doesn\'t receive captcha source')
            return None
        
        _res_body = cdp.network.get_response_body(self.captcha_res_id)
        self.captcha_res_id = None # reset captcha_res_id
        if _res_body is None:
            logger.error('response body not found')
            return None
        
        body, is_base64 = await self.page.send(_res_body)
        if not is_base64:
            logger.error('response body is not base64, can\'t decode')
            return None
        
        img_bytes = base64.b64decode(body)
        img = PIL.Image.open(io.BytesIO(img_bytes))
        res = self.ocr.classification(img).upper()
        if len(res) != 4:
            logger.error('OCR failed')
            return None
        
        return res

    async def auto_login(self):
        await self.page.get(self.LOGIN_URL)
        await self.page.get_content()

        res = await self.__solve_captcha()
        if res is None:
            logger.error('Captcha solve failed, please login manually.')
            return
        
        # run login method
        user_info = self.setting.user_info
        js_cmd = self.login_js.format(account=user_info.account, password=user_info.password, chk=res)
        logger.debug('login...')
        
        current_url = self.page.target.url 
        await self.page.evaluate(js_cmd)
        if current_url != self.page.target.url:
            logger.debug('login done')
        else:
            logger.error('login failed, please login manually.')

    async def get_ticket(self)->bool:
        logger.info('Start get ticket!!')

        while not (captcha_box := await self.page.select('input#CHK')):
            await self.page.sleep(0.5)
        
        got_ticket = False
        current_url = self.page.target.url
        while got_ticket is False:

            # captcha_box.send_keys(res)
            res = await self.__solve_captcha()
            if res is None:
                continue
            await captcha_box.send_keys(res)
            
            await self.page.evaluate('addShoppingCart()')

            if current_url != self.page.target.url:
                got_ticket = True
        logger.info('Got Ticket!!!')
        return True

    @property
    def can_buy(self):
        return 'PERFORMANCE_ID' in self.page.target.url

class Ticket_Flow_KKTix(Ticket_Flow):
    HOME_URL = "https://kktix.com/"
    LOGIN_URL = "https://kktix.com/users/sign_in"

    rigister_info_api = "https://kktix.com/g/events/{event_id}/register_info"
    base_info_api = "https://kktix.com/g/events/{event_id}/base_info"
    order_page = "https://kktix.com/events/{event_id}/registrations/{page_id}"
    order_page_id = "https://queue.kktix.com/queue/token/{token}"
    queue_api = "https://queue.kktix.com/queue/{event_id}?authenticity_token={token}"

    event_pattern = r'events/(.+)/registrations'

    @dataclass
    class Ticket:
        id: int
        ticketInventory: int
        price: int
        currency: str
        name: str
        sys_time: datetime
        start_at: datetime
        end_at_for_registration: datetime
        hasPending: bool = False

        @property
        def isStarted(self) -> bool:
            return self.sys_time > self.start_at

        @property
        def isEnded(self) -> bool:
            return self.sys_time > self.end_at_for_registration
        
        @property
        def isSoldOut(self) -> bool:
            return self.isStarted and not self.isEnded and self.ticketInventory == 0 and not self.hasPending
        
        @property
        def isOutOfStock(self) -> bool:
            return not self.isStarted or self.isEnded or self.isSoldOut

        @classmethod
        def from_json(cls, inventory: dict, base_info: dict) -> "Ticket_Flow_KKTix.ShowStatus":
            _id = str(base_info['id'])
            return cls(
                sys_time = datetime.now(timezone.utc),
                id = base_info['id'],
                name = base_info['name'],
                price = base_info['price']['cents'] / 100,
                currency = base_info['price']['currency'],
                start_at = datetime.fromisoformat(base_info['start_at']),
                end_at_for_registration = datetime.fromisoformat(base_info['end_at_for_registration']),
                ticketInventory = inventory['ticketInventory'][_id],
                hasPending=inventory['hasPending'][_id],
            )
        
        def __repr__(self):
            return f"[Ticket] {self.name} ${self.price} {self.currency}, valid {self.ticketInventory}, {self.start_at}-{self.end_at_for_registration}"

    @dataclass
    class ShowStatus:
        tickets: List["Ticket_Flow_KKTix.Ticket"]
        event_id: str
        captcha_type: int
        captcha_question: str = ""
        recaptcha_sitekey: str = ""
        registerStatus: str = "OUTSOLD_OUT"

        @classmethod
        def from_json(cls, event_id: str, inventory: dict, base_info: dict, 
                    sitekey:str="", question:str="", **args) -> "Ticket_Flow_KKTix.ShowStatus":
            return cls(
                event_id=event_id,
                captcha_type=base_info['event']['captcha_type'],
                recaptcha_sitekey=sitekey,
                captcha_question=question,
                registerStatus=inventory['registerStatus'],
                tickets=[Ticket_Flow_KKTix.Ticket.from_json(inventory, t) for t in base_info['tickets']],
            )

        def __repr__(self):
            captcha_str = f"KTX Captcha: \"{self.captcha_question}\""
            recaptcha_str = f"ReCaptcha: \"{self.recaptcha_sitekey}\""
            ticket_str = "\n".join([str(t) for t in self.tickets])

            return f'[ShowStatus] id\"{self.event_id}\" {self.registerStatus}, {len(self.tickets)} type of ticket\n'+\
                f'{"No Captcha" if self.captcha_type==0 else captcha_str if self.captcha_type==2 else recaptcha_str}\n'+\
                f'{ticket_str}\n'

    def __init__(self, page, setting):
        super().__init__(page, setting)
        self.page.add_handler(cdp.network.ResponseReceived, self.__get_response)
        self.current_event = None
        self.kktix_args = setting.kktix_args
        self.redirct_to_event_page = self.kktix_args.valid_page_url
        self.tasks = set()

    async def __get_show_info(self, event_url):
        await self.page.wait()
        
        _res = re.search(self.event_pattern, event_url)
        if _res is None:
            logger.error("Get event id failed!!")
            return
        event_id = _res.group(1)
        logger.debug(f'Getting show {event_id} info!! {event_url}')

        try:
            inventory = await self.page.evaluate('inventory.inventory')
        except Exception as _:
            logger.error('Evalute error of getting inventory')
            await self.page.sleep(0.5)
            await self.__get_show_info(event_url)
            return

        # get base info from request
        base_info = requests.get(self.base_info_api.format(event_id=event_id))
        base_info = json.loads(base_info.text)['eventData']

        status = dict(event_id=event_id, inventory=inventory, base_info=base_info)
        # check captcha type
        captcha_type = base_info['event']['captcha_type']
        if captcha_type > 0:
            # reCaptcha v2 & enterprise
            if captcha_type in [1, 3]:
                try:
                    captcha = await self.page.evaluate('TIXGLOBAL.pageInfo.recaptcha')
                finally:
                    captcha = dict(sitekeyNormal='', sitekeyAdvanced='')
                status['sitekey'] = captcha['sitekeyNormal'] if captcha_type==1 else captcha['sitekeyAdvanced']
            # KKTix captcha
            elif captcha_type == 2:
                register_info = requests.get(self.rigister_info_api.format(event_id=event_id))
                captcha = json.loads(register_info.text).get('ktx_captcha', dict(question=''))
                status['question'] = captcha['question']

        # set status to showStatus object
        self.showStatus = self.ShowStatus.from_json(**status)
        logger.debug(self.showStatus)

    async def __get_response(self, event: cdp.network.ResponseReceived):
        url = event.response.url
        if self.HOME_URL == url:
            self.showStatus = None

        elif self.HOME_URL in url: # ticket page
            if 'events' in url and url.endswith('registrations/new'):
                if any(filter(lambda t: t.get_name() == 'get_show_info', self.tasks)):
                    logger.warning('Cancel previous task')
                    for t in filter(lambda t: t.get_name() == 'get_show_info', self.tasks):
                        t.cancel()
                task = asyncio.create_task(self.__get_show_info(url), name='get_show_info')
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)

    async def auto_login(self):
        # TODO add cookie login

        await self.page.get(self.LOGIN_URL)
        await self.page.wait_for("form#new_user")
        login_js = f"""
            const userForm = document.querySelector("form#new_user");
            const formData = new FormData(userForm);
            formData.append('user[login]', '{self.setting.user_info.account}');
            formData.append('user[password]', '{self.setting.user_info.password}');
            fetch(form.action,{{
                method: "POST",
                body: formData
            }}).then(response => response.url)
            .then(url => window.location = url )
            .catch(error => {{
                console.error("Error:", error);
                userForm.submit();
            }});
        """
        await self.page.evaluate(login_js)

    async def get_ticket(self)->bool:
        await self.page.wait()
        
        # Create queue payload
        queue_payload = dict(agreeTerm=True, 
                            currency=self.showStatus.tickets[0].currency, 
                            captcha=dict(),
                            tickets=list())

        #TODO solve captcha
        if self.showStatus.captcha_type == 2:
            queue_payload['custom_captcha'] = ""
        elif self.showStatus.captcha_type in [1,3]:
            queue_payload['captcha']['responseChallenge'] = '' 
        
        for ticket in self.showStatus.tickets:
            if not ticket.isOutOfStock and ticket.name == self.kktix_args.ticket_name:
                queue_payload['tickets'].append(dict(
                    id=ticket.id,
                    quantity=min(self.kktix_args.num_of_ticket, ticket.ticketInventory),
                    invitationCodes=[],
                    member_code="",
                    use_qualification_id=None
                ))
                break

        if len(queue_payload['tickets']) == 0:
            logger.error("No tickets available")
            return False

        # Create request session for queue request.
        cookies = await self.page.get_cookies()
        if any(filter(lambda c: c.name == 'user_id_v2',cookies)) == False:
            raise Exception("User Not Login.")

        session = requests.session()
        for cookie in cookies:
            session.cookies.set(cookie.name, cookie.value)

        token = session.cookies.get('XSRF-TOKEN')

        # Queue request
        api = self.queue_api.format(event_id=self.showStatus.event_id, token=token)
        response = session.post(api, data=json.dumps(queue_payload))
        if response.status_code != 200:
            logger.error(response.text)
            return False

        page_id_token = response.json().get('token', None)
        if page_id_token is None:
            logger.error('Failed to get queue token')
            return False
        
        # Get order page parameter
        order_page_api = self.order_page_id.format(token=page_id_token)
        page_id = None
        while page_id is None: # retry until page_id is not None
            response = session.get(order_page_api)
            if response.status_code != 200:
                logger.error(response.text)
                return False
            
            page_id = response.json().get('to_param', None)
            if page_id is None:
                logger.error('Failed to get order page id')
                await self.sleep()

        redirct_url = self.order_page.format(event_id = self.showStatus.event_id, page_id=page_id)
        await self.page.get(redirct_url)
        return True

    async def start(self):
        await super().start()
        if self.redirct_to_event_page:
            await self.page.get(self.kktix_args.event_page)
            await self.__get_show_info(self.kktix_args.event_page)
            try:
                while await self.get_ticket():
                    await self.sleep()
            except Exception as e:
                logger.error(e)

    @property
    def can_buy(self):
        return self.showStatus != None and self.showStatus.registerStatus != 'SOLD_OUT'

def get_ticket_flow(
    page: Tab,
    setting: Setting,
)->Ticket_Flow:
    if setting.ticket_web == TICKET_WEB.KHAM:
        return Ticket_Flow_Kham(page, setting)
    elif setting.ticket_web == TICKET_WEB.KKTIX:
        return Ticket_Flow_KKTix(page, setting)
    else:
        logger.warning(f"Auto login is not supported for {setting.ticket_web}")
        return Ticket_Flow(page, setting)