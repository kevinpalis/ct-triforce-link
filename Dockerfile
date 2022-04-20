#author: Kevin Palis <kevin.palis@gmail.com>

#I'm using Ubuntu LTS here for maximum tools compatibility and availability. If image size is a constraint, we can switch to the basic Alpine distro

FROM ubuntu:20.04
#update and install utility packages, pip, and java
RUN DEBIAN_FRONTEND=noninteractive apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y \
 sudo \
 wget \
 software-properties-common \
 vim \
 coreutils \
 curl \
 python3-pip \
 default-jre

#make sure pip is up to date
RUN pip install --upgrade pip
#install pandas and other needed libraries
RUN pip install pandas pandasql fuzzywuzzy python-Levenshtein pytest

#copy the entrypoint/config file and make sure it can execute
COPY entrypoint.sh /root
RUN chmod 755 /root/entrypoint.sh
#copy the project files to the container
COPY triforce /home/triforce
#copy the data files to the container
COPY data /home/data
######
ENTRYPOINT ["/root/entrypoint.sh"]
