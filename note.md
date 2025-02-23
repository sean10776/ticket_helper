# Ticket Helper

## KKTIX

### 訂票網頁
`GET https://kktix.com/events/${eventname}/registrations/new`
- window.inventory: 票種資訊
    - registerStatus: 是否開放訂票
        - COMING_SOON: 尚未開賣
        - IN_STOCK: 有票
        - SOLD_OUT: 售完
- TIXGLOBAL.pageInfo.recaptcha: Google Recaptcha sitekey
    - sitekeyNormal: Google reCAPTCHA (Normal)
    - siteKeyAdvanced: Google reCAPTCHA (enterprise)

### 活動資訊 Json
`GET https://kktix.com/g/events/${eventname}/base_info`

- catpcha type:
    - 0: 不需要驗證碼
    - 1: Google reCAPTCHA (Normal)
    - 2: KKtix Captch (KKTix問答)
    - 3: Google reCAPTCHA (enterprise)

- tickets: 票種
    - start_at: 開賣時間 (UTC-0)
    - end_at_for_registration: 結束購票時間 (UTC-0)
    - price: 價格
        - cents: 價格 (分)，換算TWD要除以100

```js
srv.isStarted = function(ticket, comparedTime) {
    return !ticket.start_at || (comparedTime ? new Date(comparedTime).getTime() > new Date(ticket.start_at).getTime() : Date.now() > new Date(dateFilter(ticket.start_at, "yyyy/MM/dd HH:mm:ss")).getTime())
};
srv.isEnded = function(ticket) {
    return ticket.end_at_for_registration && new Date(dateFilter(ticket.end_at_for_registration, "yyyy/MM/dd HH:mm:ss")).getTime() < (new Date).getTime()
};
srv.isSoldOut = function(ticket, inventory) {
    return srv.isStarted(ticket) && !srv.isEnded(ticket) && 0 === inventory.ticketInventory[ticket.id] && !inventory.hasPending[ticket.id]
}
srv.isOutOfStock = function(ticket, inventory, serverTime) {
    return !srv.isStarted(ticket, serverTime) || srv.isEnded(ticket) || srv.isSoldOut(ticket, inventory)
}
```
### 購票API
`POST https://queue.kktix.com/queue/${event_name}?authenticity_token=${XSRF-TOKEN}`

```json
{ //request payload
    "agreeTerm": true,
    "currency": "TWD",
    "recaptcha": {
        "responseChallenge": "captcha result"  // if google captcha is required
    },
    "custom_captcha": "ktx captcha answer", // if kktix captcha is required
    // custom captcha question from https://kktix.com/g/events/${event_name}/register_info
    "tickets": [
        {
            "id":123456, //"ticket id"
            "quantity":0,
            "invitationCodes":[],
            "member_code":"",
            "use_qualification_id":null
        }
    ]
}
```
### 購票流程
- 到購票頁面
- (完成captcha挑戰)
- 發送Post請求取得token
- 透過`https://queue.kktix.com/queue/token/{token}`取得網頁`param`
- 透過`https://kktix.com/events/{event_id}/registrations/{param}`至付款頁面

## KHAM

## TIXCRAFT