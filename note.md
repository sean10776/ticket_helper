# Ticket Helper

## KKTIX

### 訂票網頁
`GET https://kktix.com/events/${eventname}/registrations/new`
- window.inventory: 票種資訊
    - registerStatus: 是否開放訂票
        - COMING_SOON: 尚未開賣
        - IN_STOCK: 有票
        - SOLD_OUT: 售完


### 活動資訊 Json
`GET https://kktix.com/g/events/${eventname}/base_info`

- catpcha type:
    - 0: 不需要驗證碼
    - 1: Google reCAPTCHA
- tickets: 票種
    - start_at: 開賣時間 (UTC-0)
    - price: 價格
    - 
### 購票API
`POST https://queue.kktix.com/queue/${event_name}?authenticity_token=${XSRF-TOKEN}`

## KHAM

## TIXCRAFT