#############################
# Dockerfile file escrito po Charles e Renan Berto.
# Sobe ambiente do JBOSS em container, permite acesso via SSH para troca dos aplicativos war e limpeza de cache.
# Metodo nao muito seguro que a senha esta em clean text no deploy do ambiente. Porem funcional.
# 
#
# Primera e unica vesão escrito em algum momento de 2017.... Faz tempo...
# "Charles Josiah" <charles.alandt@gmail.com>
# "Renan Berto" <renanbertoo@gmail.com>
#

FROM centos:6

MAINTAINER "Renan Berto" <renanbertoo@gmail.com>
MAINTAINER "Charles Josiah" <charles.alandt@gmail.com>

ENV JAVA_HOME=/usr/local/jdk \
    JBOSS_HOME=/usr/local/jboss-4.2.3.GA \
    JBOSS_PASSWORD=$$P@SWW)RD$$ \
    DEPLOY_DIR=/server/default/deploy \
    LOCAL_DIR=./files \
    PATH=/usr/local/jdk/bin:${PATH} \
    PATH=${JAVA_HOME}/bin:${PATH} \
    PATH=${JBOSS_HOME}/bin:${PATH} 

RUN yum update -y && \
    yum install -y unzip openssh-server sudo net-snmp  && \
    yum clean all && \
    useradd -m jboss

RUN echo 'jboss:MmBDTp35' | chpasswd && \
    echo 'jboss ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    echo "" >> /etc/bashrc && \
    echo "echo '+----------------------------------------------------------------------------+' " >> /etc/bashrc && \
    echo "echo '| Ambiente DOCKER - CASO PRECISE ALTERACOES - Contactar a equipe responsavel |' " >> /etc/bashrc && \
    echo "echo '+----------------------------------------------------------------------------+' " >> /etc/bashrc && \
    echo "" >> /etc/bashrc && \
    echo " rocommunity publicTI-124t54123 172.16.10.33 " > /etc/snmp/snmpd.conf

ADD $LOCAL_DIR/jboss $JBOSS_HOME
ADD $LOCAL_DIR/jdk $JAVA_HOME
ADD $LOCAL_DIR/oracle-ds.xml $JBOSS_HOME$DEPLOY_DIR
ADD $LOCAL_DIR/app.war $JBOSS_HOME$DEPLOY_DIR
ADD $LOCAL_DIR/app1.war $JBOSS_HOME$DEPLOY_DIR

ADD $LOCAL_DIR/app-help.war $JBOSS_HOME$DEPLOY_DIR
ADD $LOCAL_DIR/app1-help.war $JBOSS_HOME$DEPLOY_DIR

RUN sed -i 's/RUNASIS/root/' $JBOSS_HOME/bin/jboss_init_redhat.sh && \
    chown -R jboss:jboss $JBOSS_HOME && \
    chown -R jboss:jboss $JBOSS_HOME/*

RUN ln -s $JBOSS_HOME /usr/local/jboss  && \
    mv /etc/localtime /etc/localtime.bak && \
    ln -s /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime

CMD /etc/init.d/sshd start; /etc/init.d/snmpd start; $JBOSS_HOME/bin/run.sh -c default -b 0.0.0.0  2>&1 > $JBOSS_HOME/console.log


EXPOSE 8080 22 161/udp
