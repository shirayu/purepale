
# Tips to run on Linux in Windows WSL2

## CUDA setup

- Please read the [blog article](https://touch-sp.hatenablog.com/entry/2022/05/05/114358)

## Memory setting

`C:\Users\YOUR_ID\.wslconfig`

```txt
[wsl2]
memory=12GB
swap=0
```

## Port open setup

- Please read the [blog article of setting instruction](https://scratchpad.jp/ubuntu-on-windows11-13/)

1. Save the following script as ``start-wsl2.bat``

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

2. Add the task as Administrator to run the script to Windows task scheduler at Windows start
3. If you restart WSL2 manually, run ``wsl --shutdown`` in the command prompt as Administrator and run the script as Administrator
