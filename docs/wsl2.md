
# Tips to run on Linux in Windows WSL2

## CUDA setup

- Please read the [blog article](https://touch-sp.hatenablog.com/entry/2022/05/05/114358)

## Port setup

- Please read the [blog article of setting instruction](https://scratchpad.jp/ubuntu-on-windows11-13/)

```txt
; Please replace WINDOWS_MACHINE_IP_ADFRESS to the real static IP address

wsl -u root -- service cron restart

FOR /F "usebackq" %%i in (`wsl -d Ubuntu exec hostname -I`) do set IP=%%i

netsh interface portproxy delete v4tov4 listenport=22

; ssh
netsh interface portproxy add v4tov4 listenport=22 connectaddress=%IP% connectport=22 listenaddress=WINDOWS_MACHINE_IP_ADFRESS

; App port
netsh interface portproxy add v4tov4 listenport=8000 connectaddress=%IP% connectport=8000 listenaddress=WINDOWS_MACHINE_IP_ADFRESS
```
