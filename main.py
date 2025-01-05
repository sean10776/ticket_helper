import logging

import asyncio
import keyboard
import nodriver as uc

from core.setting import Setting
from core.ticket_flow import get_ticket_flow

# Setup logger
logger = logging.getLogger('core.ticket_flow')

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
ch.setFormatter(ch_formatter)

logger.addHandler(ch)

# Main function
async def main():
    ticket_setting = Setting()
    browser = await uc.start()

    ticket_helper = get_ticket_flow(browser.main_tab, ticket_setting)
    
    await ticket_helper.start()
    async def on_press():
        while not browser.stopped:
            if keyboard.is_pressed('b') and ticket_helper.can_buy:
                res = await ticket_helper.get_ticket()
                if res:
                    print('get ticket')
            await asyncio.sleep(0.001)
        print('all task stopped.')

    task = asyncio.create_task(on_press())
    
    while not ticket_helper.stop:
        await ticket_helper.sleep()

    while not browser.stopped:
        await browser.sleep()
    print('browser stopped')

    await task
    print('done')

if __name__ == '__main__':
    asyncio.run(main())