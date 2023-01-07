# escape=`

ARG WINDOWS_TAG

FROM mcr.microsoft.com/windows:${WINDOWS_TAG}
ARG IDA_DIR

SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue';"]

ENV IDA_HOME=C:\ida
COPY ${IDA_DIR} ${IDA_HOME}

RUN C:\ida\idapyswitch.exe --force-path C:\ida\python38\python3.dll

WORKDIR ${IDA_HOME}
ENTRYPOINT ["idat64.exe"]
