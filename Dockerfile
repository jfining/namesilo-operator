FROM flant/shell-operator:v1.0.1

RUN apk add --no-cache python3 curl unzip
RUN ln -s /usr/bin/python3 /usr/bin/python 
RUN python -m ensurepip --upgrade
RUN ln -s /usr/bin/pip3 /usr/bin/pip

ADD requirements.txt /hooks

WORKDIR /hooks

RUN pip install -r requirements.txt

ADD operator-hook.py /hooks

RUN chmod +x /hooks/operator-hook.py
