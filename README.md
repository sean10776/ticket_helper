# 搶票幫手

## 功能
1. 自動登入網站
1. 自動求解captcha
1. 快捷鍵自動購票

## 支援網站

- [x] [**寬宏**](https://www.kham.com.tw/)
- [ ] [**TIXCRAFT**](https://tixcraft.com/)
- [x] [**KKTIX**](https://kktix.com)

## 各網站操作方式

### 寬宏
1. 執行 `python main.py`會開啟網站並自動登入
1. 選擇想要場次、座位和票數
1. 按下快捷鍵`B`即可完成購票

### KKTIX
1. 在setting.json中填完搶票連結、票名和數量
1. 執行 `python main.py`會開啟網站並自動登入和搶票

## TODO
- 新增cookie登入
- 新增ReCaptcha V2自動解答
- UI介面
- **KKTIX**
    - Captcha自動or手動解題，**目前只支援無captcha的活動**