FROM ubuntu

RUN apt-get update
RUN apt-get install -y build-essential python2.7 python-pip git

ADD . /home/docker

RUN pip install requests

WORKDIR /home/docker
CMD python run.py
