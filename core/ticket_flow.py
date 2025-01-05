from abc import abstractmethod
import base64
import io

import ddddocr
import logging
from nodriver import Tab, cdp
import PIL.Image

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

def get_ticket_flow(
    page: Tab,
    setting: Setting,
)->Ticket_Flow:
    if setting.ticket_web == TICKET_WEB.KHAM:
        return Ticket_Flow_Kham(page, setting)
    else:
        logger.warning(f"Auto login is not supported for {setting.ticket_web}")
        return Ticket_Flow(page, setting)